#!/bin/bash

# Advanced YouTube Downloader Startup Script

echo "🚀 Starting Advanced YouTube Downloader..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

# Check if FFmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg is not installed. Audio conversion may not work."
    echo "   Please install FFmpeg for full functionality."
fi

# Create virtual environment if it doesn't exist
if [ ! -d "backend/venv" ]; then
    echo "📦 Creating Python virtual environment..."
    cd backend
    python3 -m venv venv
    cd ..
fi

# Activate virtual environment and install dependencies
echo "📦 Installing Python dependencies..."
cd backend
source venv/bin/activate

# Upgrade pip first
pip install --upgrade pip

# Try to install with simple requirements first
echo "Installing core dependencies..."
if ! pip install -r requirements-simple.txt; then
    echo "⚠️  Some packages failed to install. Trying individual installation..."
    pip install fastapi uvicorn[standard] yt-dlp pydantic sqlalchemy aiofiles python-multipart sse-starlette httpx
    echo "⚠️  Skipping Pillow and ffmpeg-python for now. You can install them manually if needed."
fi

# Create environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating environment configuration..."
    cp .env.example .env
fi

# Start backend server in background
echo "🔧 Starting backend server..."
python main.py &
BACKEND_PID=$!

cd ..

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
npm install

# Start frontend server
echo "🎨 Starting frontend server..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Advanced YouTube Downloader is starting up!"
echo ""
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://127.0.0.1:8000"
echo "📚 API Docs: http://127.0.0.1:8000/docs"
echo ""
echo "Press Ctrl+C to stop all servers"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Wait for servers
wait