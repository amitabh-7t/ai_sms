import logging
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..db import get_db, Database
from ..models import DeviceInfo, DeviceStatus
from .auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/devices", tags=["devices"])


class DeviceCreate(BaseModel):
    device_id: str
    name: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = Field(default="inactive")
    config: Optional[Dict[str, Any]] = None


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class DeviceDetail(DeviceInfo):
    config: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


def _normalize_config_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure config field is always a dict for Pydantic models."""
    if "config" in row:
        value = row["config"]
        if isinstance(value, str):
            try:
                row["config"] = json.loads(value)
            except Exception:
                # Fallback to empty dict on parse failure
                row["config"] = {}
        elif value is None:
            row["config"] = {}
    return row


async def _get_device(device_id: str, db: Database) -> Dict[str, Any]:
    device = await db.fetch_one(
        """
        SELECT id, device_id, name, location, status, last_seen, config, created_at
        FROM devices
        WHERE device_id = $1
        """,
        device_id,
    )
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found",
        )
    return _normalize_config_row(device)


@router.get("/", response_model=List[DeviceInfo])
async def list_devices(
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all registered devices"""
    devices = await db.fetch_all(
        """
        SELECT id, device_id, name, location, status, last_seen
        FROM devices
        ORDER BY created_at DESC
        """
    )
    return [DeviceInfo(**device) for device in devices]


@router.post("/", response_model=DeviceDetail, status_code=status.HTTP_201_CREATED)
async def register_device(
    payload: DeviceCreate,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Register a new capture device"""
    existing = await db.fetch_one(
        "SELECT id FROM devices WHERE device_id = $1", payload.device_id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device ID already registered",
        )
    config = payload.config or {}
    config_json = json.dumps(config)
    status_value = payload.status or "inactive"

    try:
        device = await db.fetch_one(
            """
            INSERT INTO devices (device_id, name, location, status, config, last_seen)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6)
            RETURNING id, device_id, name, location, status, last_seen, config, created_at
            """,
            payload.device_id,
            payload.name,
            payload.location,
            status_value,
            config_json,
            None,
        )
        device = _normalize_config_row(device)
        logger.info(f"Registered device {payload.device_id}")
        return DeviceDetail(**device)
    except Exception as exc:
        logger.error(f"Failed to register device {payload.device_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register device",
        )


@router.get("/{device_id}", response_model=DeviceDetail)
async def get_device(
    device_id: str,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get device details"""
    device = await _get_device(device_id, db)
    return DeviceDetail(**device)


@router.put("/{device_id}", response_model=DeviceDetail)
async def update_device(
    device_id: str,
    payload: DeviceUpdate,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update device metadata/config"""
    await _get_device(device_id, db)

    updates = []
    params: List[Any] = []

    if payload.name is not None:
        updates.append(f"name = ${len(params) + 1}")
        params.append(payload.name)
    if payload.location is not None:
        updates.append(f"location = ${len(params) + 1}")
        params.append(payload.location)
    if payload.status is not None:
        updates.append(f"status = ${len(params) + 1}")
        params.append(payload.status)
    if payload.config is not None:
        updates.append(f"config = ${len(params) + 1}::jsonb")
        params.append(json.dumps(payload.config))

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )

    params.extend([device_id])

    query = f"""
        UPDATE devices
        SET {', '.join(updates)}
        WHERE device_id = ${len(params)}
        RETURNING id, device_id, name, location, status, last_seen, config, created_at
    """

    try:
        device = await db.fetch_one(query, *params)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Device not found"
            )
        device = _normalize_config_row(device)
        logger.info(f"Updated device {device_id}")
        return DeviceDetail(**device)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to update device {device_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update device",
        )


@router.get("/{device_id}/status", response_model=DeviceStatus)
async def get_device_status(
    device_id: str,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return device activity based on recent events"""
    await _get_device(device_id, db)

    last_event = await db.fetch_one(
        """
        SELECT ts
        FROM events
        WHERE source_device = $1
        ORDER BY ts DESC
        LIMIT 1
        """,
        device_id,
    )

    events_count = await db.fetch_one(
        """
        SELECT COUNT(*) as count
        FROM events
        WHERE source_device = $1
          AND ts >= NOW() - INTERVAL '1 hour'
        """,
        device_id,
    )

    last_event_time = last_event["ts"] if last_event else None
    is_capturing = False

    if last_event_time:
        delta = datetime.utcnow() - last_event_time
        is_capturing = delta <= timedelta(minutes=2)
        await db.execute(
            "UPDATE devices SET last_seen = $1 WHERE device_id = $2",
            last_event_time,
            device_id,
        )

    return DeviceStatus(
        device_id=device_id,
        is_capturing=is_capturing,
        last_event_time=last_event_time,
        events_count=events_count["count"] if events_count else 0,
    )


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: str,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete a registered device"""
    await _get_device(device_id, db)

    try:
        await db.execute("DELETE FROM devices WHERE device_id = $1", device_id)
        logger.info(f"Deleted device {device_id}")
    except Exception as exc:
        logger.error(f"Failed to delete device {device_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete device",
        )

