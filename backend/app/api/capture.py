import json
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from ..db import get_db, Database
from ..models import CaptureSessionCreate, CaptureSessionResponse
from ..services.process_manager import process_manager
from .auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/capture", tags=["capture"])


def _normalize_session(session: dict) -> dict:
    if session is None:
        return session
    config = session.get("config")
    if isinstance(config, str):
        try:
            session["config"] = json.loads(config)
        except json.JSONDecodeError:
            session["config"] = {}
    elif config is None:
        session["config"] = {}
    return session


@router.post(
    "/sessions",
    response_model=CaptureSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_capture_session(
    payload: CaptureSessionCreate,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Start capture session and launch capture worker."""
    device = await db.fetch_one(
        "SELECT device_id, config FROM devices WHERE device_id = $1",
        payload.device_id,
    )
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {payload.device_id} not found",
        )

    existing = process_manager.get_status(payload.device_id)
    if existing and existing.get("is_running"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Capture already running for {payload.device_id}",
        )

    config = payload.config or {}
    session = await db.fetch_one(
        """
        INSERT INTO capture_sessions (device_id, started_at, status, config)
        VALUES ($1, $2, $3, $4)
        RETURNING *
        """,
        payload.device_id,
        datetime.utcnow(),
        "running",
        json.dumps(config) if config else None,
    )

    success = await process_manager.start_capture(
        payload.device_id,
        config,
        session["id"],
    )

    if not success:
        await db.execute(
            "UPDATE capture_sessions SET status = $1, stopped_at = $2 WHERE id = $3",
            "failed",
            datetime.utcnow(),
            session["id"],
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start capture process",
        )

    await db.execute(
        """
        UPDATE devices
        SET status = 'active', last_seen = NOW()
        WHERE device_id = $1
        """,
        payload.device_id,
    )

    logger.info(
        "Capture session %s started for device %s",
        session["id"],
        payload.device_id,
    )
    return CaptureSessionResponse(**_normalize_session(session))


@router.get("/sessions", response_model=List[CaptureSessionResponse])
async def list_capture_sessions(
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List recent capture sessions"""
    sessions = await db.fetch_all(
        """
        SELECT id, device_id, status, started_at, stopped_at, config
        FROM capture_sessions
        ORDER BY started_at DESC
        LIMIT 100
        """
    )
    return [CaptureSessionResponse(**_normalize_session(session)) for session in sessions]


@router.get("/sessions/{session_id}", response_model=CaptureSessionResponse)
async def get_capture_session(
    session_id: int,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Fetch single capture session"""
    session = await db.fetch_one(
        """
        SELECT id, device_id, status, started_at, stopped_at, config
        FROM capture_sessions
        WHERE id = $1
        """,
        session_id,
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capture session not found",
        )
    return CaptureSessionResponse(**_normalize_session(session))


@router.put("/sessions/{session_id}/stop", response_model=CaptureSessionResponse)
async def stop_capture_session(
    session_id: int,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Stop capture session and terminate subprocess."""
    session = await db.fetch_one(
        "SELECT * FROM capture_sessions WHERE id = $1",
        session_id,
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capture session not found",
        )
    if session["status"] != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is not running (status: {session['status']})",
        )

    success = process_manager.stop_capture(session["device_id"])

    await db.execute(
        "UPDATE capture_sessions SET status = $1, stopped_at = $2 WHERE id = $3",
        "stopped" if success else "failed",
        datetime.utcnow(),
        session_id,
    )

    await db.execute(
        """
        UPDATE devices
        SET status = CASE
            WHEN EXISTS (
                SELECT 1 FROM capture_sessions
                WHERE device_id = $1 AND status = 'running'
            ) THEN 'active'
            ELSE 'inactive'
        END
        WHERE device_id = $1
        """,
        session["device_id"],
    )

    updated = await db.fetch_one(
        "SELECT * FROM capture_sessions WHERE id = $1",
        session_id,
    )
    logger.info("Capture session %s stopped for %s", session_id, session["device_id"])
    return CaptureSessionResponse(**_normalize_session(updated))


@router.get("/status/{device_id}")
async def get_capture_status(
    device_id: str,
    current_user: dict = Depends(get_current_user),
):
    status_data = process_manager.get_status(device_id)
    if not status_data:
        return {
            "device_id": device_id,
            "is_running": False,
            "message": "No active capture",
        }
    return status_data


@router.get("/status")
async def get_all_capture_status(
    current_user: dict = Depends(get_current_user),
):
    return process_manager.get_all_status()

