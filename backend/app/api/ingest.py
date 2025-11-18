from fastapi import APIRouter, Header, HTTPException, status, Depends
from typing import Optional, List
import json
import logging
from datetime import datetime
from pathlib import Path

from ..models import IngestRequest, IngestResponse, EventData
from ..config import config
from ..db import get_db, Database
from ..services.publisher import publish_event

logger = logging.getLogger(__name__)
router = APIRouter()

def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify ingest API key"""
    if x_api_key != config.INGEST_API_KEY:
        logger.warning(f"Invalid API key attempted: {x_api_key}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return x_api_key

async def insert_event(event: EventData, db: Database) -> bool:
    """Insert single event into database"""
    try:
        # Parse timestamp
        try:
            ts = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
        except:
            ts = datetime.utcnow()
        
        # Prepare raw data
        raw_data = event.raw if event.raw else event.dict()
        
        # Insert into events table
        await db.execute(
            """
            INSERT INTO events (
                ts, student_id, face_conf, emotion, emotion_confidence,
                probabilities, metrics, head_pose, ear, source_device, raw
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
            ts,
            event.student_id,
            event.face_match_confidence,
            event.emotion,
            event.emotion_confidence,
            json.dumps(event.probabilities),
            json.dumps(event.metrics),
            json.dumps(event.head_pose) if event.head_pose else None,
            event.ear,
            event.source_device,
            json.dumps(raw_data)
        )
        
        return True
    except Exception as e:
        logger.error(f"Failed to insert event: {e}")
        return False

def write_to_fallback(event: EventData):
    """Write event to fallback JSONL file"""
    try:
        Path(config.DATA_DIR).mkdir(parents=True, exist_ok=True)
        with open(config.SESSION_LOG, "a") as f:
            f.write(json.dumps(event.dict()) + "\n")
        logger.info("Event written to fallback log")
    except Exception as e:
        logger.error(f"Failed to write to fallback: {e}")

@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    request: IngestRequest,
    api_key: str = Depends(verify_api_key),
    db: Database = Depends(get_db)
):
    """
    Ingest event data from edge devices
    Accepts single event or array of events
    """
    
    events: List[EventData] = []
    
    # Handle batch or single event
    if request.events:
        events = request.events
    else:
        # Single event
        try:
            event = EventData(
                timestamp=request.timestamp or datetime.utcnow().isoformat(),
                student_id=request.student_id,
                face_match_confidence=request.face_match_confidence,
                emotion=request.emotion,
                emotion_confidence=request.emotion_confidence,
                probabilities=request.probabilities or {},
                metrics=request.metrics or {},
                ear=request.ear,
                head_pose=request.head_pose,
                source_device=request.source_device or "default",
                raw=request.raw
            )
            events.append(event)
        except Exception as e:
            logger.error(f"Failed to parse single event: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event data: {str(e)}"
            )
    
    if not events:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No events provided"
        )
    
    inserted = 0
    failed = 0
    
    for event in events:
        # Try to insert into database
        success = await insert_event(event, db)
        
        if success:
            inserted += 1
            
            # Publish to Redis for live feed
            try:
                await publish_event(event.source_device, event.dict())
            except Exception as e:
                logger.error(f"Failed to publish to Redis: {e}")
        else:
            failed += 1
            # Write to fallback
            write_to_fallback(event)
    
    logger.info(f"Ingested {inserted} events, {failed} failed")
    
    return IngestResponse(
        status="ok",
        inserted=inserted,
        message=f"{failed} events written to fallback" if failed > 0 else None
    )