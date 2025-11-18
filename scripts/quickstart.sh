#!/bin/bash

# AiSMS Quick Start Script

set -e

echo "🚀 AiSMS Quick Start"
echo "===================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if emotion model exists
if [ ! -f "models/emotion_model.pt" ]; then
    echo "⚠️  Warning: emotion_model.pt not found in models/ directory"
    echo "   The system will still run, but emotion detection may not work."
    echo ""
fi

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created. Please edit it with your configuration if needed."
    echo ""
fi

# Create necessary directories
echo "📁 Creating data directories..."
mkdir -p data/enrollment_photos
mkdir -p models
echo "✅ Directories created."
echo ""

# Start services
echo "🐳 Starting Docker containers..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✅ Services are running!"
    echo ""
    echo "📊 Service Status:"
    docker-compose ps
    echo ""
    echo "🌐 Access URLs:"
    echo "   Frontend:  http://localhost:3000"
    echo "   Backend:   http://localhost:8001"
    echo "   API Docs:  http://localhost:8001/docs"
    echo ""
    echo "🔑 Default Login Credentials:"
    echo "   Email:     admin@aisms.local"
    echo "   Password:  admin123"
    echo ""
    echo "📚 Next Steps:"
    echo "   1. Open http://localhost:3000 in your browser"
    echo "   2. Login with the credentials above"
    echo "   3. Navigate to 'Enroll' to add students"
    echo "   4. Run your capture script to send events"
    echo ""
    echo "💡 Useful Commands:"
    echo "   View logs:        docker-compose logs -f"
    echo "   Stop services:    docker-compose down"
    echo "   Restart:          docker-compose restart"
    echo "   Clean everything: docker-compose down -v"
    echo ""
    echo "✨ Setup complete! Happy monitoring! ✨"
else
    echo "❌ Some services failed to start. Check logs with:"
    echo "   docker-compose logs"
    exit 1
fi