-- Capture & Device support

CREATE TABLE IF NOT EXISTS devices (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255),
    location VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'inactive',
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_seen TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen DESC);

CREATE TABLE IF NOT EXISTS capture_sessions (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(100) REFERENCES devices(device_id) ON DELETE SET NULL,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    stopped_at TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    config JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_capture_sessions_device ON capture_sessions(device_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_capture_sessions_status ON capture_sessions(status);

