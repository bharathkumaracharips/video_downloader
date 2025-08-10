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

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )