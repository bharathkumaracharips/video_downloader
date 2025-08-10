"""
Format analysis and conversion API routes
"""

from fastapi import APIRouter, HTTPException
import logging
from typing import Dict, List

from core.models import URLRequest
from core.downloader import downloader

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/analyze")
async def analyze_formats(request: URLRequest):
    """Analyze available formats for a URL"""
    try:
        info = await downloader.get_video_info(str(request.url))
        
        # Categorize formats
        video_only = []
        audio_only = []
        combined = []
        
        for fmt in info.formats:
            format_data = {
                "format_id": fmt.format_id,
                "ext": fmt.ext,
                "resolution": fmt.resolution,
                "fps": fmt.fps,
                "vcodec": fmt.vcodec,
                "acodec": fmt.acodec,
                "filesize": fmt.filesize or fmt.filesize_approx,
                "tbr": fmt.tbr,
                "vbr": fmt.vbr,
                "abr": fmt.abr,
                "quality": fmt.quality,
                "format_note": fmt.format_note
            }
            
            if fmt.has_video and fmt.has_audio:
                combined.append(format_data)
            elif fmt.has_video:
                video_only.append(format_data)
            elif fmt.has_audio:
                audio_only.append(format_data)
        
        # Sort formats by quality
        combined.sort(key=lambda x: (x.get('quality') or 0, x.get('tbr') or 0), reverse=True)
        video_only.sort(key=lambda x: (x.get('quality') or 0, x.get('vbr') or 0), reverse=True)
        audio_only.sort(key=lambda x: (x.get('abr') or 0), reverse=True)
        
        return {
            "video_info": {
                "title": info.title,
                "duration": info.duration,
                "uploader": info.uploader,
                "upload_date": info.upload_date,
                "view_count": info.view_count,
                "thumbnail": info.thumbnail
            },
            "formats": {
                "combined": combined,
                "video_only": video_only,
                "audio_only": audio_only
            },
            "recommendations": {
                "best_quality": combined[0] if combined else None,
                "best_audio": audio_only[0] if audio_only else None,
                "smallest_size": min(combined, key=lambda x: x.get('filesize') or float('inf')) if combined else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error analyzing formats: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/presets")
async def get_format_presets():
    """Get predefined format presets"""
    return {
        "video_presets": [
            {
                "name": "Best Quality",
                "format": "best",
                "description": "Highest quality available"
            },
            {
                "name": "1080p",
                "format": "best[height<=1080]",
                "description": "Full HD quality"
            },
            {
                "name": "720p",
                "format": "best[height<=720]",
                "description": "HD quality"
            },
            {
                "name": "480p",
                "format": "best[height<=480]",
                "description": "Standard quality"
            },
            {
                "name": "360p",
                "format": "best[height<=360]",
                "description": "Lower quality, smaller file"
            }
        ],
        "audio_presets": [
            {
                "name": "Best Audio",
                "format": "bestaudio",
                "description": "Highest audio quality"
            },
            {
                "name": "MP3 320kbps",
                "format": "bestaudio[abr<=320]",
                "codec": "mp3",
                "description": "High quality MP3"
            },
            {
                "name": "MP3 192kbps",
                "format": "bestaudio[abr<=192]",
                "codec": "mp3",
                "description": "Standard quality MP3"
            },
            {
                "name": "AAC",
                "format": "bestaudio[acodec=aac]",
                "codec": "aac",
                "description": "AAC format"
            }
        ],
        "custom_formats": {
            "description": "You can use custom format selectors",
            "examples": [
                "best[ext=mp4]",
                "worst[ext=webm]",
                "bestvideo[height<=720]+bestaudio",
                "best[filesize<100M]"
            ]
        }
    }

@router.post("/compare")
async def compare_formats(request: URLRequest, format_ids: List[str]):
    """Compare specific formats"""
    try:
        info = await downloader.get_video_info(str(request.url))
        
        # Find requested formats
        selected_formats = []
        for fmt in info.formats:
            if fmt.format_id in format_ids:
                selected_formats.append({
                    "format_id": fmt.format_id,
                    "ext": fmt.ext,
                    "resolution": fmt.resolution,
                    "fps": fmt.fps,
                    "vcodec": fmt.vcodec,
                    "acodec": fmt.acodec,
                    "filesize": fmt.filesize or fmt.filesize_approx,
                    "tbr": fmt.tbr,
                    "vbr": fmt.vbr,
                    "abr": fmt.abr,
                    "quality": fmt.quality,
                    "format_note": fmt.format_note,
                    "has_video": fmt.has_video,
                    "has_audio": fmt.has_audio
                })
        
        if not selected_formats:
            raise HTTPException(status_code=404, detail="No matching formats found")
        
        # Calculate comparison metrics
        comparison = {
            "formats": selected_formats,
            "comparison": {
                "highest_quality": max(selected_formats, key=lambda x: x.get('quality') or 0),
                "smallest_file": min(selected_formats, key=lambda x: x.get('filesize') or float('inf')),
                "highest_bitrate": max(selected_formats, key=lambda x: x.get('tbr') or 0),
                "best_video": max([f for f in selected_formats if f['has_video']], 
                                key=lambda x: x.get('vbr') or 0, default=None),
                "best_audio": max([f for f in selected_formats if f['has_audio']], 
                                key=lambda x: x.get('abr') or 0, default=None)
            }
        }
        
        return comparison
        
    except Exception as e:
        logger.error(f"Error comparing formats: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/codecs")
async def get_supported_codecs():
    """Get information about supported codecs"""
    return {
        "video_codecs": {
            "h264": {
                "name": "H.264/AVC",
                "description": "Most compatible video codec",
                "quality": "Good",
                "compatibility": "Excellent"
            },
            "h265": {
                "name": "H.265/HEVC",
                "description": "Modern codec with better compression",
                "quality": "Excellent",
                "compatibility": "Good"
            },
            "vp9": {
                "name": "VP9",
                "description": "Google's open-source codec",
                "quality": "Excellent",
                "compatibility": "Good"
            },
            "av01": {
                "name": "AV1",
                "description": "Next-generation codec",
                "quality": "Excellent",
                "compatibility": "Limited"
            }
        },
        "audio_codecs": {
            "aac": {
                "name": "AAC",
                "description": "Advanced Audio Coding",
                "quality": "Good",
                "compatibility": "Excellent"
            },
            "mp3": {
                "name": "MP3",
                "description": "Most compatible audio format",
                "quality": "Good",
                "compatibility": "Excellent"
            },
            "opus": {
                "name": "Opus",
                "description": "Modern, efficient codec",
                "quality": "Excellent",
                "compatibility": "Good"
            },
            "flac": {
                "name": "FLAC",
                "description": "Lossless compression",
                "quality": "Perfect",
                "compatibility": "Good"
            }
        }
    }