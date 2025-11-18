from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .config import config
from .db import db
from .api import auth, ingest, metrics, ws, devices, capture
from .api.enroll import router as enroll_router
from .services.process_manager import process_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting AiSMS Backend...")
    await db.connect()
    logger.info("Database connected")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AiSMS Backend...")
    logger.info("Stopping capture workers...")
    process_manager.stop_all()
    await db.disconnect()
    logger.info("Database disconnected")

app = FastAPI(
    title="AiSMS Backend API",
    version="1.0.0",
    description="Full-stack web application for AI Student Monitoring System",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(ingest.router, tags=["ingest"])
app.include_router(metrics.router, tags=["metrics"])
app.include_router(ws.router, tags=["websocket"])
app.include_router(enroll_router, tags=["enrollment"])
app.include_router(devices.router, tags=["devices"])
app.include_router(capture.router, tags=["capture"])

@app.get("/")
async def root():
    return {
        "service": "AiSMS Backend API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_status = "connected" if db.pool else "disconnected"
    return {
        "status": "healthy",
        "database": db_status
    }