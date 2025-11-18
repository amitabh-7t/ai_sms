from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

# Auth Models
class UserSignup(BaseModel):
    email: str
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None

# Event Models
class EventData(BaseModel):
    timestamp: str
    student_id: Optional[str] = None
    face_match_confidence: Optional[float] = None
    emotion: str
    emotion_confidence: float
    probabilities: Dict[str, float]
    metrics: Dict[str, float]
    ear: Optional[float] = None
    head_pose: Optional[Dict[str, float]] = None
    source_device: str = "default"
    raw: Optional[Dict[str, Any]] = None

class IngestRequest(BaseModel):
    events: Optional[List[EventData]] = None
    # Support single event as well
    timestamp: Optional[str] = None
    student_id: Optional[str] = None
    face_match_confidence: Optional[float] = None
    emotion: Optional[str] = None
    emotion_confidence: Optional[float] = None
    probabilities: Optional[Dict[str, float]] = None
    metrics: Optional[Dict[str, float]] = None
    ear: Optional[float] = None
    head_pose: Optional[Dict[str, float]] = None
    source_device: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None

class IngestResponse(BaseModel):
    status: str
    inserted: int
    message: Optional[str] = None

# Metrics Models
class MetricsQuery(BaseModel):
    from_time: Optional[str] = None
    to_time: Optional[str] = None
    granularity: str = "minute"

class StudentMetrics(BaseModel):
    timestamp: str
    avg_engagement: float
    avg_boredom: float
    avg_frustration: float
    samples: int

class ClassOverview(BaseModel):
    device_id: str
    avg_engagement: float
    avg_boredom: float
    avg_frustration: float
    total_samples: int
    active_students: int
    alerts: List[Dict[str, Any]]

# Device & Capture Models
class DeviceInfo(BaseModel):
    id: int
    device_id: str
    name: Optional[str] = None
    location: Optional[str] = None
    status: str
    last_seen: Optional[datetime] = None

class CaptureSessionCreate(BaseModel):
    device_id: str
    config: Optional[Dict[str, Any]] = None

class CaptureSessionResponse(BaseModel):
    id: int
    device_id: Optional[str]
    status: str
    started_at: datetime
    stopped_at: Optional[datetime] = None
    config: Optional[Dict[str, Any]] = None

class DeviceStatus(BaseModel):
    device_id: str
    is_capturing: bool
    last_event_time: Optional[datetime] = None
    events_count: int = 0