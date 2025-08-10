"""
Video download API routes
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any
import os
import logging

from core.models import VideoDownloadRequest, DownloadResponse, URLRequest, VideoInfo
from core.downloader import downloader
from services.queue_manager import queue_manager
from core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/info", response_model=VideoInfo)
async def get_video_info(request: URLRequest):
    """Get video information without downloading"""
    try:
        info = await downloader.get_video_info(str(request.url))
        return info
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/download", response_model=DownloadResponse)
async def download_video(request: VideoDownloadRequest):
    """Download video with specified quality (handles separate video+audio streams)"""
    try:
        # For high quality videos, we need to download video and audio separately and merge
        # Use bestvideo+bestaudio format for quality downloads
        if request.quality.value in ["best", "best[height<=1080]", "best[height<=720]", "best[height<=480]"]:
            format_selector = f"bestvideo[height<={request.quality.value.split('<=')[1].rstrip(']')}]+bestaudio/best" if "height<=" in request.quality.value else "bestvideo+bestaudio/best"
        else:
            format_selector = request.format_id if request.format_id else request.quality.value
        
        # Clean filename template - remove special characters and limit length
        options = {
            'format': format_selector,
            'outtmpl': request.output_template or os.path.join(
                settings.DOWNLOAD_DIR, 
                '%(title).100s.%(ext)s'  # Limit title to 100 chars
            ),
            'restrictfilenames': True,  # Remove special characters
            'merge_output_format': 'mp4',  # Ensure merged output is mp4
        }
        
        # Add subtitle options if specified
        if request.subtitle_langs:
            options.update({
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': request.subtitle_langs,
            })
        
        # Add to queue
        download_request = {
            'type': 'video_merge',
            'url': str(request.url),
            'options': options,
            'priority': 1
        }
        
        download_id = await queue_manager.add_to_queue(download_request)
        
        return DownloadResponse(
            download_id=download_id,
            status="pending",
            message="Video download added to queue (will merge video+audio if needed)"
        )
        
    except Exception as e:
        logger.error(f"Error starting video download: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/download/direct")
async def download_video_direct(request: VideoDownloadRequest):
    """Download video directly without queue (for immediate downloads)"""
    try:
        # Prepare download options
        options = {
            'format': request.quality.value if not request.format_id else request.format_id,
            'outtmpl': request.output_template or os.path.join(
                settings.DOWNLOAD_DIR, 
                '%(title)s.%(ext)s'
            ),
        }
        
        # Add subtitle options if specified
        if request.subtitle_langs:
            options.update({
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': request.subtitle_langs,
            })
        
        # Download directly
        filename = await downloader.download_video(str(request.url), options)
        
        return DownloadResponse(
            download_id="direct",
            status="completed",
            message="Video downloaded successfully",
            filename=os.path.basename(filename),
            file_path=filename,
            download_url=f"/downloads/{os.path.basename(filename)}"
        )
        
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/formats/{video_id}")
async def get_video_formats(video_id: str):
    """Get available formats for a YouTube video by ID"""
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        info = await downloader.get_video_info(url)
        
        # Group formats by type
        video_formats = [f for f in info.formats if f.has_video and not f.has_audio]
        audio_formats = [f for f in info.formats if f.has_audio and not f.has_video]
        combined_formats = [f for f in info.formats if f.has_video and f.has_audio]
        
        return {
            "video_info": {
                "title": info.title,
                "duration": info.duration,
                "uploader": info.uploader,
                "thumbnail": info.thumbnail
            },
            "formats": {
                "combined": combined_formats,
                "video_only": video_formats,
                "audio_only": audio_formats
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting video formats: {e}")
        raise HTTPException(status_code=400, detail=str(e))