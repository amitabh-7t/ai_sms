import json
import logging
from typing import Dict, Any, Optional

from redis.asyncio import Redis

from ..config import config

logger = logging.getLogger(__name__)

# Global Redis connection for publishing
redis_client: Optional[Redis] = None

async def get_redis():
    """Get or create Redis client"""
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(config.REDIS_URL, decode_responses=True)
        logger.info("Redis publisher connected")
    return redis_client

async def publish_event(device_id: str, event_data: Dict[str, Any]):
    """
    Publish event to Redis channel for WebSocket broadcasting
    Channel format: live:{device_id}
    """
    try:
        redis = await get_redis()
        channel = f"live:{device_id}"
        message = json.dumps(event_data)
        
        await redis.publish(channel, message)
        logger.debug(f"Published event to {channel}")
    
    except Exception as e:
        logger.error(f"Failed to publish to Redis: {e}")
        # Don't raise - publishing is non-critical

async def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
        logger.info("Redis publisher disconnected")