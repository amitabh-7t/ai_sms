from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from datetime import datetime, timedelta
import json
import logging

from ..models import StudentMetrics, ClassOverview
from ..db import get_db, Database
from ..api.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/students/{student_id}/metrics")
async def get_student_metrics(
    student_id: str,
    from_time: Optional[str] = Query(None, alias="from"),
    to_time: Optional[str] = Query(None, alias="to"),
    granularity: str = Query("minute"),
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get aggregated metrics for a student
    """
    
    # Parse time range
    if not from_time:
        from_dt = datetime.utcnow() - timedelta(hours=1)
    else:
        try:
            from_dt = datetime.fromisoformat(from_time.replace('Z', '+00:00'))
        except:
            from_dt = datetime.utcnow() - timedelta(hours=1)
    
    if not to_time:
        to_dt = datetime.utcnow()
    else:
        try:
            to_dt = datetime.fromisoformat(to_time.replace('Z', '+00:00'))
        except:
            to_dt = datetime.utcnow()
    
    # Try to fetch from aggregates_minute table first
    if granularity == "minute":
        try:
            rows = await db.fetch_all(
                """
                SELECT 
                    minute_ts as timestamp,
                    avg_engagement,
                    avg_boredom,
                    avg_frustration,
                    sample_count as samples
                FROM aggregates_minute
                WHERE student_id = $1 AND minute_ts >= $2 AND minute_ts <= $3
                ORDER BY minute_ts
                """,
                student_id, from_dt, to_dt
            )
            
            if rows:
                return {"metrics": rows}
        except Exception as e:
            logger.warning(f"Aggregates table not available: {e}")
    
    # Fallback: compute from events table
    try:
        rows = await db.fetch_all(
            """
            SELECT 
                date_trunc('minute', ts) as timestamp,
                AVG((metrics->>'engagement')::float) as avg_engagement,
                AVG((metrics->>'boredom')::float) as avg_boredom,
                AVG((metrics->>'frustration')::float) as avg_frustration,
                COUNT(*) as samples
            FROM events
            WHERE student_id = $1 AND ts >= $2 AND ts <= $3
            GROUP BY date_trunc('minute', ts)
            ORDER BY timestamp
            """,
            student_id, from_dt, to_dt
        )
        
        return {"metrics": rows}
    except Exception as e:
        logger.error(f"Failed to fetch metrics: {e}")
        return {"metrics": []}

@router.get("/classes/{device_id}/overview")
async def get_class_overview(
    device_id: str,
    from_time: Optional[str] = Query(None, alias="from"),
    to_time: Optional[str] = Query(None, alias="to"),
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get class-level overview and alerts
    """
    
    # Parse time range
    if not from_time:
        from_dt = datetime.utcnow() - timedelta(hours=1)
    else:
        try:
            from_dt = datetime.fromisoformat(from_time.replace('Z', '+00:00'))
        except:
            from_dt = datetime.utcnow() - timedelta(hours=1)
    
    if not to_time:
        to_dt = datetime.utcnow()
    else:
        try:
            to_dt = datetime.fromisoformat(to_time.replace('Z', '+00:00'))
        except:
            to_dt = datetime.utcnow()
    
    # Get class metrics
    try:
        class_data = await db.fetch_one(
            """
            SELECT 
                AVG((metrics->>'engagement')::float) as avg_engagement,
                AVG((metrics->>'boredom')::float) as avg_boredom,
                AVG((metrics->>'frustration')::float) as avg_frustration,
                COUNT(*) as total_samples,
                COUNT(DISTINCT student_id) as active_students
            FROM events
            WHERE source_device = $1 AND ts >= $2 AND ts <= $3 AND student_id IS NOT NULL
            """,
            device_id, from_dt, to_dt
        )
        
        # Get recent alerts
        alerts = await db.fetch_all(
            """
            SELECT alert_type, severity, student_id, message, created_at
            FROM alerts
            WHERE source_device = $1 AND created_at >= $2
            ORDER BY created_at DESC
            LIMIT 10
            """,
            device_id, from_dt
        )
        
        return {
            "device_id": device_id,
            "avg_engagement": class_data.get("avg_engagement", 0.0) or 0.0,
            "avg_boredom": class_data.get("avg_boredom", 0.0) or 0.0,
            "avg_frustration": class_data.get("avg_frustration", 0.0) or 0.0,
            "total_samples": class_data.get("total_samples", 0) or 0,
            "active_students": class_data.get("active_students", 0) or 0,
            "alerts": alerts
        }
    except Exception as e:
        logger.error(f"Failed to fetch class overview: {e}")
        return {
            "device_id": device_id,
            "avg_engagement": 0.0,
            "avg_boredom": 0.0,
            "avg_frustration": 0.0,
            "total_samples": 0,
            "active_students": 0,
            "alerts": []
        }

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get overall dashboard summary"""
    
    try:
        # Last hour stats
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        summary = await db.fetch_one(
            """
            SELECT 
                COUNT(DISTINCT student_id) as active_students,
                COUNT(DISTINCT source_device) as active_devices,
                COUNT(*) as total_events,
                AVG((metrics->>'engagement')::float) as avg_engagement,
                AVG((metrics->>'risk')::float) as avg_risk
            FROM events
            WHERE ts >= $1 AND student_id IS NOT NULL
            """,
            one_hour_ago
        )
        
        # Get recent alerts count
        alert_count = await db.fetch_one(
            """
            SELECT COUNT(*) as count
            FROM alerts
            WHERE created_at >= $1 AND severity IN ('high', 'critical')
            """,
            one_hour_ago
        )
        
        return {
            "active_students": summary.get("active_students", 0) or 0,
            "active_devices": summary.get("active_devices", 0) or 0,
            "total_events": summary.get("total_events", 0) or 0,
            "avg_engagement": summary.get("avg_engagement", 0.0) or 0.0,
            "avg_risk": summary.get("avg_risk", 0.0) or 0.0,
            "recent_alerts": alert_count.get("count", 0) or 0
        }
    except Exception as e:
        logger.error(f"Failed to fetch dashboard summary: {e}")
        return {
            "active_students": 0,
            "active_devices": 0,
            "total_events": 0,
            "avg_engagement": 0.0,
            "avg_risk": 0.0,
            "recent_alerts": 0
        }