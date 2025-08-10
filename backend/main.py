"""
Advanced Multi-Mode YouTube Downloader
Built with FastAPI and yt-dlp
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn

from api.routes import video, audio, playlist, live, formats, queue
from core.config import settings
from core.database import init_db
from core.logger import setup_logging
from core.downloader import downloader

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    await init_db()
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Advanced YouTube Downloader",
    description="Multi-mode downloader with yt-dlp integration",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/downloads", StaticFiles(directory="downloads"), name="downloads")

# Include routers
app.include_router(video.router, prefix="/api/video", tags=["video"])
app.include_router(audio.router, prefix="/api/audio", tags=["audio"])
app.include_router(playlist.router, prefix="/api/playlist", tags=["playlist"])
app.include_router(live.router, prefix="/api/live", tags=["live"])
app.include_router(formats.router, prefix="/api/formats", tags=["formats"])
app.include_router(queue.router, prefix="/api/queue", tags=["queue"])

@app.get("/")
async def root():
    return {"message": "Advanced YouTube Downloader API", "version": "2.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/system/status")
async def system_status():
    """Get system resource status"""
    try:
        import psutil
        
        # Get memory info
        memory = psutil.virtual_memory()
        
        # Get CPU info
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get disk info for downloads directory
        disk = psutil.disk_usage(settings.DOWNLOAD_DIR)
        
        return {
            "status": "healthy",
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "free_gb": round(memory.available / (1024**3), 2)
            },
            "cpu": {
                "percent": cpu_percent
            },
            "disk": {
                "total": disk.total,
                "free": disk.free,
                "percent": round((disk.used / disk.total) * 100, 2),
                "free_gb": round(disk.free / (1024**3), 2)
            }
        }
    except ImportError:
        return {"status": "healthy", "note": "psutil not available for detailed monitoring"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/system/cleanup")
async def cleanup_system():
    """Clean up system resources and hanging processes"""
    try:
        # Clean up downloader processes
        downloader._cleanup_processes()
        
        # Force garbage collection
        import gc
        gc.collect()
        
        return {"status": "success", "message": "System cleanup completed"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )