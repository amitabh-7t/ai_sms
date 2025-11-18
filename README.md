# AiSMS - AI Student Monitoring System

Full-stack web application for real-time student engagement monitoring with face recognition, emotion detection, and live metrics.

## 🏗️ Architecture

- **Backend**: FastAPI (Python 3.10+) with async PostgreSQL and Redis
- **Frontend**: React + Vite with Tailwind CSS
- **Database**: PostgreSQL for persistent storage
- **Cache/PubSub**: Redis for real-time WebSocket broadcasting
- **Containerization**: Docker + Docker Compose

## 📁 Project Structure

```
ai_sms/
├── backend/               # FastAPI backend
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── services/     # Background services
│   │   ├── migrations/   # Database migrations
│   │   ├── main.py       # App entry point
│   │   ├── config.py     # Configuration
│   │   ├── db.py         # Database helpers
│   │   └── models.py     # Pydantic models
│   ├── Dockerfile
│   └── requirements.txt
├── web/                   # React frontend
│   ├── src/
│   │   ├── pages/        # Page components
│   │   ├── components/   # Reusable components
│   │   ├── api.js        # API client
│   │   └── ws.js         # WebSocket client
│   ├── Dockerfile
│   └── package.json
├── src/                   # Existing capture code
├── models/                # PyTorch models
├── data/                  # Data storage
├── docker-compose.yml
└── README.md
```

## 🚀 Quick Start with Docker

### Prerequisites

- Docker and Docker Compose installed
- Your `emotion_model.pt` in the `models/` folder

### 1. Clone and Setup

```bash
cd ai_sms
cp .env.example .env
# Edit .env with your configuration
```

### 2. Start All Services

```bash
docker-compose up -d
```

This will start:

- PostgreSQL (port 5432)
- Redis (port 6379)
- Backend API (port 8001)
- Frontend Web (port 3000)

### 3. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs
- **Default Login**: admin@aisms.local / admin123

### 4. Stop Services

```bash
docker-compose down
```

## 💻 Local Development (Without Docker)

### Backend Setup

1. **Create Virtual Environment**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install Dependencies**

```bash
pip install -r requirements.txt
```

3. **Setup Database**

```bash
# Install PostgreSQL locally or use Docker for just the database
docker run -d \
  --name aisms_postgres \
  -e POSTGRES_DB=aismsdb \
  -e POSTGRES_USER=aismsuser \
  -e POSTGRES_PASSWORD=aismspass \
  -p 5432:5432 \
  postgres:15-alpine

# Run migrations
psql -h localhost -U aismsuser -d aismsdb -f app/migrations/001_create_tables.sql
```

4. **Setup Redis**

```bash
# Install Redis locally or use Docker
docker run -d --name aisms_redis -p 6379:6379 redis:7-alpine
```

5. **Set Environment Variables**

```bash
export DATABASE_URL="postgresql://aismsuser:aismspass@localhost:5432/aismsdb"
export REDIS_URL="redis://localhost:6379"
export SECRET_KEY="your-secret-key"
export INGEST_API_KEY="your-ingest-key"
export MODEL_PATH="../models/emotion_model.pt"
```

6. **Run Backend**

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend Setup

1. **Install Dependencies**

```bash
cd web
npm install
```

2. **Set Environment Variables**
   Create `web/.env`:

```
VITE_API_BASE=http://localhost:8001
VITE_WS_BASE=ws://localhost:8001
```

3. **Run Frontend**

```bash
npm run dev
```

Frontend will be available at http://localhost:3000

## 📊 Database Migrations

### Manual Migration

```bash
# Connect to PostgreSQL
psql -h localhost -U aismsuser -d aismsdb

# Run migration file
\i backend/app/migrations/001_create_tables.sql
```

### Using Docker

Migrations run automatically when starting with docker-compose.

## 🔑 API Authentication

### Default Admin Credentials

- Email: `admin@aisms.local`
- Password: `admin123`

### Creating New Users

```bash
curl -X POST http://localhost:8001/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure-password",
    "full_name": "John Doe"
  }'
```

### Getting Access Token

```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@aisms.local",
    "password": "admin123"
  }'
```

## 📡 API Endpoints

### Authentication

- `POST /auth/signup` - Register new user
- `POST /auth/login` - Login and get JWT token
- `GET /auth/me` - Get current user info

### Enrollment

- `GET /enroll` - Enrollment form page
- `POST /enroll` - Upload student photos
- `GET /students` - List enrolled students

### Ingest

- `POST /ingest` - Ingest events from edge devices (requires X-API-KEY header)

### Metrics

- `GET /students/{id}/metrics` - Get student metrics
- `GET /classes/{device_id}/overview` - Get class overview
- `GET /dashboard/summary` - Get dashboard summary

### WebSocket

- `WS /ws/live?room={device_id}` - Live event feed

## 🔌 Integration with Edge Devices

### Sending Events to Backend

Your edge capture script should POST events to `/ingest`:

```python
import requests
import json

event_data = {
    "timestamp": "2024-01-15T10:30:00Z",
    "student_id": "12345",
    "face_match_confidence": 0.95,
    "emotion": "Happy",
    "emotion_confidence": 0.87,
    "probabilities": {
        "Happy": 0.87,
        "Neutral": 0.10,
        "Sad": 0.03
    },
    "metrics": {
        "engagement": 0.75,
        "boredom": 0.12,
        "frustration": 0.05
    },
    "ear": 0.25,
    "head_pose": {
        "yaw": 5.2,
        "pitch": -2.1,
        "roll": 0.5
    },
    "source_device": "classroom_1"
}

response = requests.post(
    "http://localhost:8001/ingest",
    headers={"X-API-KEY": "your-ingest-key"},
    json=event_data
)

print(response.json())
```

### Batch Ingestion

```python
events = [event1, event2, event3]
response = requests.post(
    "http://localhost:8001/ingest",
    headers={"X-API-KEY": "your-ingest-key"},
    json={"events": events}
)
```

## 🔧 Configuration

### Environment Variables

| Variable         | Description                  | Default                                                   |
| ---------------- | ---------------------------- | --------------------------------------------------------- |
| `DATABASE_URL`   | PostgreSQL connection string | `postgresql://aismsuser:aismspass@localhost:5432/aismsdb` |
| `REDIS_URL`      | Redis connection string      | `redis://localhost:6379`                                  |
| `SECRET_KEY`     | JWT signing key              | `dev-secret-key`                                          |
| `INGEST_API_KEY` | API key for ingest endpoint  | `dev-ingest-key`                                          |
| `MODEL_PATH`     | Path to emotion model        | `./models/emotion_model.pt`                               |
| `VITE_API_BASE`  | Frontend API base URL        | `http://localhost:8001`                                   |
| `VITE_WS_BASE`   | Frontend WebSocket base URL  | `ws://localhost:8001`                                     |

## 🧪 Running Background Services

### Aggregator Service (Optional)

Computes per-minute aggregates and checks for alerts:

```bash
cd backend
python -m app.services.aggregator
```

Or use Celery for production:

```bash
celery -A app.services.aggregator worker --loglevel=info
```

## 📦 Building for Production

### Backend

```bash
cd backend
docker build -t aisms-backend .
docker run -p 8001:8001 \
  -e DATABASE_URL="..." \
  -e REDIS_URL="..." \
  -e SECRET_KEY="..." \
  aisms-backend
```

### Frontend

```bash
cd web
npm run build
# Serve dist/ folder with nginx or any static server
```

## 🐛 Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Test connection
psql -h localhost -U aismsuser -d aismsdb
```

### Redis Connection Issues

```bash
# Check if Redis is running
docker ps | grep redis

# Test connection
redis-cli ping
```

### WebSocket Not Connecting

- Ensure Redis is running
- Check CORS settings in backend
- Verify WebSocket URL in frontend

### Face Recognition Not Working

- Ensure `data/known_encodings.json` exists
- Check that students are enrolled with photos
- Verify `face_recognition` library is installed

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a pull request.

## 📞 Support

For issues or questions, please open a GitHub issue.
