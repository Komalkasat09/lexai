#!/bin/bash

# Legal Research Platform - Quick Start
# =====================================

echo "🏛️  Legal Research Platform - Starting..."
echo ""

# Check if we're in the right directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ Error: Run this script from the legal-website root directory"
    exit 1
fi

# Function to check if port is in use
check_port() {
    lsof -i :$1 > /dev/null 2>&1
    return $?
}

# Check if ports are available
if check_port 8000; then
    echo "⚠️  Port 8000 is in use. Backend may already be running."
    echo "   To stop: lsof -ti:8000 | xargs kill -9"
    echo ""
fi

if check_port 3000; then
    echo "⚠️  Port 3000 is in use. Frontend may already be running."
    echo "   To stop: lsof -ti:3000 | xargs kill -9"
    echo ""
fi

# Start backend
echo "🚀 Starting Backend (http://localhost:8000)..."
cd backend
python app.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 3

# Check if backend is running
if check_port 8000; then
    echo "✅ Backend started successfully!"
else
    echo "❌ Backend failed to start. Check logs above."
    exit 1
fi

# Start frontend
echo ""
echo "🚀 Starting Frontend (http://localhost:3000)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "=" * 80
echo "🎉 Legal Research Platform is starting!"
echo "=" * 80
echo ""
echo "📍 Frontend:  http://localhost:3000"
echo "📍 Backend:   http://localhost:8000"
echo "📍 API Docs:  http://localhost:8000/api/docs"
echo ""
echo "To stop, press Ctrl+C or run:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "Logs will appear below..."
echo "=" * 80

# Wait for processes
wait
