@echo off
REM Advanced YouTube Downloader Startup Script for Windows

echo 🚀 Starting Advanced YouTube Downloader...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.8+ first.
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js is not installed. Please install Node.js 18+ first.
    pause
    exit /b 1
)

REM Check if FFmpeg is installed
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  FFmpeg is not installed. Audio conversion may not work.
    echo    Please install FFmpeg for full functionality.
)

REM Create virtual environment if it doesn't exist
if not exist "backend\venv" (
    echo 📦 Creating Python virtual environment...
    cd backend
    python -m venv venv
    cd ..
)

REM Activate virtual environment and install dependencies
echo 📦 Installing Python dependencies...
cd backend
call venv\Scripts\activate
pip install -r requirements.txt

REM Create environment file if it doesn't exist
if not exist ".env" (
    echo ⚙️  Creating environment configuration...
    copy .env.example .env
)

REM Start backend server
echo 🔧 Starting backend server...
start /b python main.py

cd ..

REM Install Node.js dependencies
echo 📦 Installing Node.js dependencies...
call npm install

REM Start frontend server
echo 🎨 Starting frontend server...
start /b npm run dev

echo.
echo ✅ Advanced YouTube Downloader is starting up!
echo.
echo 🌐 Frontend: http://localhost:3000
echo 🔧 Backend API: http://127.0.0.1:8000
echo 📚 API Docs: http://127.0.0.1:8000/docs
echo.
echo Press any key to stop all servers...
pause >nul

REM Cleanup
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1