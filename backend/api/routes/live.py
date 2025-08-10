"""
Live stream download API routes
"""

from fastapi import APIRouter, HTTPException
import logging

from core.models import LiveStreamRequest, DownloadResponse, URLRequest
from core.downloader import downloader
from services.queue_manager import queue_manager
from core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/info")
async def get_live_stream_info(request: URLRequest):
    """Get live stream information"""
    try:
        info = await downloader.get_video_info(str(request.url))
        
        return {
            "title": info.title,
            "uploader": info.uploader,
            "is_live": info.is_live,
            "live_status": info.live_status,
            "thumbnail": info.thumbnail,
            "description": info.description,
            "available_formats": [
                {
                    "format_id": f.format_id,
                    "ext": f.ext,
                    "resolution": f.resolution,
                    "fps": f.fps,
                    "has_video": f.has_video,
                    "has_audio": f.has_audio
                }
                for f in info.formats
                if f.has_video or f.has_audio
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting live stream info: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/download", response_model=DownloadResponse)
async def download_live_stream(request: LiveStreamRequest):
    """Download live stream"""
    try:
        # Prepare download options for live streams
        options = {
            'format': request.quality.value,
            'outtmpl': f'{settings.DOWNLOAD_DIR}/live/%(title)s_%(upload_date)s.%(ext)s',
            'live_from_start': True,
            'wait_for_video': (5, 30) if request.wait_for_live else None,
        }
        
        # Add duration limit if specified
        if request.duration:
            options['external_downloader_args'] = ['-t', str(request.duration)]
        
        # Add to queue with high priority for live streams
        download_request = {
            'type': 'live',
            'url': str(request.url),
            'options': options,
            'priority': 10  # High priority for live streams
        }
        
        download_id = await queue_manager.add_to_queue(download_request)
        
        return DownloadResponse(
            download_id=download_id,
            status="pending",
            message="Live stream download added to queue"
        )
        
    except Exception as e:
        logger.error(f"Error starting live stream download: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/record")
async def record_live_stream(request: LiveStreamRequest):
    """Record live stream with advanced options"""
    try:
        # Advanced recording options
        options = {
            'format': request.quality.value,
            'outtmpl': f'{settings.DOWNLOAD_DIR}/live/%(title)s_%(upload_date)s_%(timestamp)s.%(ext)s',
            'live_from_start': True,
            'wait_for_video': (10, 60) if request.wait_for_live else None,
            'fragment_retries': 10,
            'retry_sleep_functions': {'http': lambda n: 2**n},
            'keepvideo': True,  # Keep original video file
        }
        
        # Duration handling
        if request.duration:
            options['match_filter'] = lambda info_dict: None if info_dict.get('duration', 0) <= request.duration else "Duration limit exceeded"
        
        # Add metadata
        options['writeinfojson'] = True
        options['writethumbnail'] = True
        
        download_request = {
            'type': 'live_record',
            'url': str(request.url),
            'options': options,
            'priority': 10
        }
        
        download_id = await queue_manager.add_to_queue(download_request)
        
        return DownloadResponse(
            download_id=download_id,
            status="pending",
            message="Live stream recording started"
        )
        
    except Exception as e:
        logger.error(f"Error starting live stream recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/check/{video_id}")
async def check_live_status(video_id: str):
    """Check if a YouTube video is currently live"""
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        info = await downloader.get_video_info(url)
        
        return {
            "video_id": video_id,
            "title": info.title,
            "is_live": info.is_live,
            "live_status": info.live_status,
            "uploader": info.uploader,
            "scheduled_start_time": info.description if "scheduled" in (info.live_status or "").lower() else None
        }
        
    except Exception as e:
        logger.error(f"Error checking live status: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/upcoming")
async def get_upcoming_streams():
    """Get information about upcoming live streams (placeholder)"""
    # This would require additional API integration or database
    return {
        "message": "Upcoming streams feature requires additional implementation",
        "suggestion": "Use channel URLs to monitor for live streams"
    }