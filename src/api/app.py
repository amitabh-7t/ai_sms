"""
Main FastAPI app entrypoint.

This stitches together all API routers (currently enrollment).
Run with:
    uvicorn src.api.app:app --host 0.0.0.0 --port 8001 --reload
"""

from fastapi import FastAPI
from .enroll_api import router as enroll_router

app = FastAPI(
    title="AiSMS Enrollment API",
    version="1.0.0",
    description="Upload student photos + student ID for enrollment"
)

# Register routers
app.include_router(enroll_router)