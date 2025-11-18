-- AiSMS Database Schema

-- Users table for authentication
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Students table
CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255),
    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Events table - stores all captured events
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMP NOT NULL,
    student_id VARCHAR(100),
    face_conf FLOAT,
    emotion VARCHAR(50),
    emotion_confidence FLOAT,
    probabilities JSONB,
    metrics JSONB,
    head_pose JSONB,
    ear FLOAT,
    source_device VARCHAR(100) DEFAULT 'default',
    raw JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for events table
CREATE INDEX IF NOT EXISTS idx_events_student_ts ON events(student_id, ts);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts DESC);
CREATE INDEX IF NOT EXISTS idx_events_device ON events(source_device, ts DESC);

-- Aggregates per minute
CREATE TABLE IF NOT EXISTS aggregates_minute (
    id BIGSERIAL PRIMARY KEY,
    minute_ts TIMESTAMP NOT NULL,
    student_id VARCHAR(100) NOT NULL,
    avg_engagement FLOAT,
    avg_boredom FLOAT,
    avg_frustration FLOAT,
    avg_attentiveness FLOAT,
    sample_count INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(minute_ts, student_id)
);

-- Index for aggregates
CREATE INDEX IF NOT EXISTS idx_aggregates_student_ts ON aggregates_minute(student_id, minute_ts);

-- Alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id BIGSERIAL PRIMARY KEY,
    student_id VARCHAR(100),
    source_device VARCHAR(100),
    alert_type VARCHAR(50),
    severity VARCHAR(20), -- low, medium, high, critical
    message TEXT,
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP,
    acknowledged_by INT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for alerts
CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_student ON alerts(student_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_device ON alerts(source_device, created_at DESC);

-- Create default admin user (password: admin123)
-- Hash for 'admin123' using bcrypt
INSERT INTO users (email, password_hash, full_name, is_admin)
VALUES ('admin@aisms.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLHJ4jWG', 'System Admin', TRUE)
ON CONFLICT (email) DO NOTHING;