"""
Audio download API routes
"""

from fastapi import APIRouter, HTTPException
import os
import logging

from core.models import AudioDownloadRequest, MusicDownloadRequest, SponsorBlockMusicRequest, DownloadResponse, URLRequest
from core.downloader import downloader
from services.queue_manager import queue_manager
from core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/download", response_model=DownloadResponse)
async def download_audio(request: AudioDownloadRequest):
    """Download audio with specified quality and format"""
    try:
        # Prepare download options for audio extraction
        options = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': request.format,
                'preferredquality': request.quality if request.quality != 'best' else '320',
            }],
            'outtmpl': request.output_template or os.path.join(
                settings.DOWNLOAD_DIR, 
                '%(title).100s.%(ext)s'
            ),
            'restrictfilenames': True,
            'windowsfilenames': True,
        }
        
        # Add to queue
        download_request = {
            'type': 'audio',
            'url': str(request.url),
            'options': options,
            'priority': 1
        }
        
        download_id = await queue_manager.add_to_queue(download_request)
        
        return DownloadResponse(
            download_id=download_id,
            status="pending",
            message="Audio download added to queue"
        )
        
    except Exception as e:
        logger.error(f"Error starting audio download: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/download/direct")
async def download_audio_direct(request: AudioDownloadRequest):
    """Download audio directly without queue"""
    try:
        # Prepare download options for audio extraction
        options = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': request.format,
                'preferredquality': request.quality if request.quality != 'best' else '320',
            }],
            'outtmpl': request.output_template or os.path.join(
                settings.DOWNLOAD_DIR, 
                '%(title).100s.%(ext)s'
            ),
            'restrictfilenames': True,
            'windowsfilenames': True,
        }
        
        # Download directly
        filename = await downloader.download_video(str(request.url), options)
        
        # The filename might change after post-processing
        base_name = os.path.splitext(filename)[0]
        audio_filename = f"{base_name}.{request.format}"
        
        return DownloadResponse(
            download_id="direct",
            status="completed",
            message="Audio downloaded successfully",
            filename=os.path.basename(audio_filename),
            file_path=audio_filename,
            download_url=f"/downloads/{os.path.basename(audio_filename)}"
        )
        
    except Exception as e:
        logger.error(f"Error downloading audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extract")
async def extract_audio_from_video(request: URLRequest):
    """Extract audio from video URL and return best available audio formats"""
    try:
        info = await downloader.get_video_info(str(request.url))
        
        # Filter audio-only formats
        audio_formats = [
            {
                'format_id': f.format_id,
                'ext': f.ext,
                'abr': f.abr,
                'acodec': f.acodec,
                'filesize': f.filesize or f.filesize_approx,
                'quality': f.quality
            }
            for f in info.formats 
            if f.has_audio and not f.has_video
        ]
        
        # Sort by quality (bitrate)
        audio_formats.sort(key=lambda x: x.get('abr', 0) or 0, reverse=True)
        
        return {
            "title": info.title,
            "duration": info.duration,
            "audio_formats": audio_formats,
            "recommended_format": audio_formats[0] if audio_formats else None
        }
        
    except Exception as e:
        logger.error(f"Error extracting audio info: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/download/music/sponsorblock", response_model=DownloadResponse)
async def download_music_with_sponsorblock(request: SponsorBlockMusicRequest):
    """Download music with SponsorBlock integration to automatically remove unwanted segments"""
    try:
        filename = await downloader.download_music_with_sponsorblock(
            str(request.url),
            request.quality,
            request.format,
            request.remove_categories,
            request.mark_categories,
            request.sponsorblock_api
        )
        
        return DownloadResponse(
            download_id="sponsorblock_music_direct",
            status="completed",
            message="Music downloaded with SponsorBlock processing",
            filename=os.path.basename(filename),
            file_path=filename,
            download_url=f"/downloads/{os.path.basename(filename)}"
        )
        
    except Exception as e:
        logger.error(f"Error downloading music with SponsorBlock: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sponsorblock/categories")
async def get_sponsorblock_categories():
    """Get available SponsorBlock categories with descriptions"""
    return {
        "categories": {
            "sponsor": {
                "name": "Sponsor",
                "description": "Paid promotion, paid referrals and direct advertisements",
                "color": "#00d400",
                "recommended_for_music": True
            },
            "intro": {
                "name": "Intermission/Intro Animation", 
                "description": "An interval without actual content. Could be a pause, static frame, repeating animation",
                "color": "#00ffff",
                "recommended_for_music": True
            },
            "outro": {
                "name": "Endcards/Credits",
                "description": "Information that appears on screen after the main content",
                "color": "#0202ed",
                "recommended_for_music": True
            },
            "selfpromo": {
                "name": "Unpaid/Self Promotion",
                "description": "Self promotion: unpaid, charity, community, etc.",
                "color": "#ffff00",
                "recommended_for_music": True
            },
            "preview": {
                "name": "Preview/Recap",
                "description": "Quick recap of the previous video, or a preview of what's coming up",
                "color": "#008fd6",
                "recommended_for_music": False
            },
            "filler": {
                "name": "Filler Tangent/Jokes",
                "description": "Tangential scenes added only for filler or humor that are not required",
                "color": "#7300ff",
                "recommended_for_music": False
            },
            "interaction": {
                "name": "Interaction Reminder",
                "description": "When there is a short reminder to like, subscribe or interact",
                "color": "#cc00ff",
                "recommended_for_music": True
            },
            "music_offtopic": {
                "name": "Non-Music Section",
                "description": "Only for music videos. This includes introductions or outros in music videos",
                "color": "#ff9900",
                "recommended_for_music": True
            }
        },
        "presets": {
            "music_clean": {
                "name": "Clean Music",
                "description": "Perfect for music downloads - removes all non-music content",
                "remove": ["sponsor", "intro", "outro", "selfpromo", "interaction", "music_offtopic"],
                "mark": []
            },
            "music_minimal": {
                "name": "Minimal Cleaning",
                "description": "Only removes obvious promotions and sponsors",
                "remove": ["sponsor", "selfpromo"],
                "mark": []
            },
            "music_aggressive": {
                "name": "Aggressive Cleaning",
                "description": "Removes everything except the core music content",
                "remove": ["sponsor", "intro", "outro", "selfpromo", "preview", "interaction", "music_offtopic"],
                "mark": []
            }
        }
    }

@router.get("/quality-presets")
async def get_audio_quality_presets():
    """Get available audio quality presets"""
    return {
        "qualities": [
            {"value": "best", "label": "Best Available", "description": "Highest quality available"},
            {"value": "320", "label": "320 kbps", "description": "High quality MP3"},
            {"value": "256", "label": "256 kbps", "description": "Good quality"},
            {"value": "192", "label": "192 kbps", "description": "Standard quality"},
            {"value": "128", "label": "128 kbps", "description": "Lower quality, smaller file"}
        ],
        "formats": [
            {"value": "mp3", "label": "MP3", "description": "Most compatible format"},
            {"value": "aac", "label": "AAC", "description": "Good quality, smaller files"},
            {"value": "flac", "label": "FLAC", "description": "Lossless compression"},
            {"value": "opus", "label": "Opus", "description": "Modern, efficient codec"},
            {"value": "wav", "label": "WAV", "description": "Uncompressed audio"}
        ]
    }