"""
aggregator.py

Background service to compute per-minute aggregates from events table
This is a stub - can be run as a separate process or Celery task

To run manually:
    python -m backend.app.services.aggregator

For production, use Celery or run as scheduled task
"""

import asyncio
import logging
from datetime import datetime, timedelta

from ..db import Database
from ..config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def compute_minute_aggregates(db: Database, minutes_back: int = 5):
    """
    Compute aggregates for the last N minutes
    Inserts into aggregates_minute table
    """
    
    try:
        # Get time range
        to_time = datetime.utcnow()
        from_time = to_time - timedelta(minutes=minutes_back)
        
        # Compute aggregates per student per minute (all 9 metrics)
        await db.execute(
            """
            INSERT INTO aggregates_minute (
                minute_ts, student_id, avg_engagement, avg_boredom,
                avg_frustration, avg_attentiveness, avg_positivity,
                avg_volatility, avg_distraction, avg_fatigue, avg_risk,
                sample_count
            )
            SELECT
                date_trunc('minute', ts) as minute_ts,
                student_id,
                AVG((metrics->>'engagement')::float) as avg_engagement,
                AVG((metrics->>'boredom')::float) as avg_boredom,
                AVG((metrics->>'frustration')::float) as avg_frustration,
                AVG((metrics->>'attentiveness')::float) as avg_attentiveness,
                AVG((metrics->>'positivity')::float) as avg_positivity,
                AVG((metrics->>'volatility')::float) as avg_volatility,
                AVG((metrics->>'distraction')::float) as avg_distraction,
                AVG((metrics->>'fatigue')::float) as avg_fatigue,
                AVG((metrics->>'risk')::float) as avg_risk,
                COUNT(*) as sample_count
            FROM events
            WHERE ts >= $1 AND ts < $2 AND student_id IS NOT NULL
            GROUP BY date_trunc('minute', ts), student_id
            ON CONFLICT (minute_ts, student_id) DO UPDATE SET
                avg_engagement = EXCLUDED.avg_engagement,
                avg_boredom = EXCLUDED.avg_boredom,
                avg_frustration = EXCLUDED.avg_frustration,
                avg_attentiveness = EXCLUDED.avg_attentiveness,
                avg_positivity = EXCLUDED.avg_positivity,
                avg_volatility = EXCLUDED.avg_volatility,
                avg_distraction = EXCLUDED.avg_distraction,
                avg_fatigue = EXCLUDED.avg_fatigue,
                avg_risk = EXCLUDED.avg_risk,
                sample_count = EXCLUDED.sample_count
            """,
            from_time, to_time
        )
        
        logger.info(f"Computed aggregates for {from_time} to {to_time}")
    
    except Exception as e:
        logger.error(f"Failed to compute aggregates: {e}")

async def check_and_create_alerts(db: Database):
    """
    Check recent metrics and create alerts for at-risk students
    """
    
    try:
        # Get students with high risk in last 10 minutes
        ten_min_ago = datetime.utcnow() - timedelta(minutes=10)
        
        at_risk = await db.fetch_all(
            """
            SELECT 
                student_id,
                source_device,
                AVG((metrics->>'risk')::float) as avg_risk,
                AVG((metrics->>'frustration')::float) as avg_frustration,
                AVG((metrics->>'boredom')::float) as avg_boredom
            FROM events
            WHERE ts >= $1 AND student_id IS NOT NULL
            GROUP BY student_id, source_device
            HAVING AVG((metrics->>'risk')::float) > 0.7
            """,
            ten_min_ago
        )
        
        for student in at_risk:
            # Check if alert already exists recently
            existing = await db.fetch_one(
                """
                SELECT id FROM alerts
                WHERE student_id = $1 AND created_at >= $2
                LIMIT 1
                """,
                student["student_id"],
                ten_min_ago
            )
            
            if not existing:
                # Create new alert
                severity = "critical" if student["avg_risk"] > 0.85 else "high"
                message = f"High risk score: {student['avg_risk']:.2f}"
                
                await db.execute(
                    """
                    INSERT INTO alerts (
                        student_id, source_device, alert_type, 
                        severity, message, created_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    student["student_id"],
                    student["source_device"],
                    "high_risk",
                    severity,
                    message,
                    datetime.utcnow()
                )
                
                logger.info(f"Created alert for student {student['student_id']}")
    
    except Exception as e:
        logger.error(f"Failed to check alerts: {e}")

async def run_aggregator_loop():
    """
    Main aggregator loop - runs continuously
    """
    
    db = Database()
    await db.connect()
    
    logger.info("Aggregator service started")
    
    try:
        while True:
            # Compute aggregates every minute
            await compute_minute_aggregates(db, minutes_back=5)
            
            # Check for alerts every 2 minutes
            await check_and_create_alerts(db)
            
            # Sleep for 60 seconds
            await asyncio.sleep(60)
    
    except KeyboardInterrupt:
        logger.info("Aggregator service stopped")
    
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(run_aggregator_loop())