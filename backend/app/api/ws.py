from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Set, Optional
import asyncio
import json
import logging

from redis.asyncio import Redis

from ..config import config

logger = logging.getLogger(__name__)
router = APIRouter()

# Connection manager for WebSocket clients
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.redis: Optional[Redis] = None
        self.pubsub = None
    
    async def connect_redis(self):
        """Initialize Redis connection"""
        if not self.redis:
            self.redis = Redis.from_url(config.REDIS_URL, decode_responses=True)
            logger.info("Redis connected for WebSocket")
    
    async def disconnect_redis(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis disconnected")
    
    async def connect(self, websocket: WebSocket, room: str):
        """Accept WebSocket connection and add to room"""
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = set()
        self.active_connections[room].add(websocket)
        logger.info(f"Client connected to room: {room}")
    
    def disconnect(self, websocket: WebSocket, room: str):
        """Remove WebSocket from room"""
        if room in self.active_connections:
            self.active_connections[room].discard(websocket)
            if not self.active_connections[room]:
                del self.active_connections[room]
        logger.info(f"Client disconnected from room: {room}")
    
    async def broadcast_to_room(self, room: str, message: str):
        """Send message to all clients in a room"""
        if room not in self.active_connections:
            return
        
        disconnected = set()
        for connection in self.active_connections[room]:
            try:
                await connection.send_text(message)
            except:
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection, room)
    
    async def subscribe_and_forward(self, room: str):
        """Subscribe to Redis channel and forward messages to WebSocket clients"""
        try:
            await self.connect_redis()
            
            # Create pubsub instance
            pubsub = self.redis.pubsub()
            channel = f"live:{room}"
            
            await pubsub.subscribe(channel)
            logger.info(f"Subscribed to Redis channel: {channel}")
            
            # Listen for messages
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    await self.broadcast_to_room(room, data)
                
                # Check if room still has connections
                if room not in self.active_connections or not self.active_connections[room]:
                    break
            
            await pubsub.unsubscribe(channel)
            logger.info(f"Unsubscribed from Redis channel: {channel}")
        
        except Exception as e:
            logger.error(f"Error in Redis subscription: {e}")

# Global connection manager
manager = ConnectionManager()

@router.websocket("/ws/live")
async def websocket_live(
    websocket: WebSocket,
    room: str = Query(...)
):
    """
    WebSocket endpoint for live event feed
    Connect with: ws://localhost:8001/ws/live?room=device_id
    """
    await manager.connect(websocket, room)
    
    # Start Redis subscription in background
    subscription_task = asyncio.create_task(manager.subscribe_and_forward(room))
    
    try:
        # Keep connection alive and handle client messages
        while True:
            data = await websocket.receive_text()
            # Echo back or handle client messages if needed
            logger.debug(f"Received from client in room {room}: {data}")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
        subscription_task.cancel()
        logger.info(f"Client disconnected from room: {room}")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, room)
        subscription_task.cancel()

@router.on_event("startup")
async def startup_event():
    """Initialize Redis on startup"""
    await manager.connect_redis()

@router.on_event("shutdown")
async def shutdown_event():
    """Close Redis on shutdown"""
    await manager.disconnect_redis()