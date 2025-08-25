"""
Browser-assisted download API routes
Handles downloads using video info extracted from the user's browser
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, Optional, List
import os
import asyncio
import requests
import subprocess
from datetime import datetime
import uuid
import tempfile
import shutil

from core.config import settings
import json
import re

router = APIRouter()

# YouTube InnerTube API configuration
INNERTUBE_API_KEY = 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8'
INNERTUBE_CONTEXT = {
    'client': {
        'clientName': 'WEB',
        'clientVersion': '2.20231219.04.00',
        'hl': 'en',
        'gl': 'US',
        'utcOffsetMinutes': 0,
    },
    'user': {
        'lockedSafetyMode': False,
    },
    'request': {
        'useSsl': True,
    },
}

class BrowserVideoFormat(BaseModel):
    format_id: str
    ext: str
    resolution: str
    fps: int
    vcodec: str
    acodec: str
    filesize: Optional[int] = None
    url: Optional[str] = None
    has_video: bool
    has_audio: bool
    format_note: str
    quality: Optional[str] = None

class BrowserVideoInfo(BaseModel):
    id: str
    title: str
    duration: int
    uploader: str
    thumbnail: str
    formats: List[BrowserVideoFormat]
    streamingData: Optional[Dict[str, Any]] = None

class BrowserDownloadRequest(BaseModel):
    video_info: BrowserVideoInfo
    selected_format_id: str
    merge_audio: bool = True
    audio_format_id: Optional[str] = None
    filename: Optional[str] = None

class BrowserDownloadResponse(BaseModel):
    download_id: str
    filename: str
    status: str
    message: str

# Store active downloads
active_downloads = {}

class BrowserDownloadProgress:
    def __init__(self, download_id: str):
        self.download_id = download_id
        self.status = "starting"
        self.progress = 0
        self.message = ""
        self.output_file = None
        self.error = None

async def download_from_browser_info(download_id: str, video_info: BrowserVideoInfo, 
                                   selected_format_id: str, merge_audio: bool = True,
                                   audio_format_id: Optional[str] = None,
                                   custom_filename: Optional[str] = None):
    """Download video using browser-extracted info"""
    progress = BrowserDownloadProgress(download_id)
    active_downloads[download_id] = progress
    
    temp_dir = None
    
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix=f"browser_dl_{download_id}_")
        progress.message = f"Created temp directory: {temp_dir}"
        
        # Find selected format
        selected_format = None
        audio_format = None
        
        for fmt in video_info.formats:
            if fmt.format_id == selected_format_id:
                selected_format = fmt
            if audio_format_id and fmt.format_id == audio_format_id:
                audio_format = fmt
        
        if not selected_format:
            raise Exception(f"Selected format {selected_format_id} not found")
        
        progress.status = "downloading"
        progress.message = "Downloading video..."
        
        # Download video
        video_file = None
        if selected_format.url:
            try:
                video_file = await download_stream(selected_format.url, temp_dir, f"video.{selected_format.ext}")
                progress.progress = 50
                progress.message = f"Downloaded video ({selected_format.resolution})"
            except Exception as e:
                progress.message = f"Video download failed: {e}"
                print(f"[Error] Video download failed: {e}")
        else:
            progress.message = "No video URL available - stream may have expired"
            print("[Error] No video URL in selected format")
        
        # Download audio if needed
        audio_file = None
        if merge_audio and not selected_format.has_audio:
            if audio_format and audio_format.url:
                progress.message = "Downloading audio..."
                audio_file = await download_stream(audio_format.url, temp_dir, f"audio.{audio_format.ext}")
                progress.progress = 75
            else:
                # Find best audio format
                best_audio = None
                for fmt in video_info.formats:
                    if fmt.has_audio and not fmt.has_video:
                        if not best_audio or (fmt.filesize and best_audio.filesize and fmt.filesize > best_audio.filesize):
                            best_audio = fmt
                
                if best_audio and best_audio.url:
                    progress.message = "Downloading best audio..."
                    audio_file = await download_stream(best_audio.url, temp_dir, f"audio.{best_audio.ext}")
                    progress.progress = 75
        
        # Merge if needed
        output_filename = custom_filename or f"{video_info.title}.mp4"
        output_filename = "".join(c for c in output_filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        output_path = os.path.join(settings.DOWNLOAD_DIR, output_filename)
        
        if audio_file and video_file:
            progress.message = "Merging video and audio..."
            await merge_video_audio(video_file, audio_file, output_path)
        elif video_file:
            progress.message = "Copying video file..."
            shutil.copy2(video_file, output_path)
        else:
            raise Exception("No video file downloaded")
        
        progress.status = "completed"
        progress.progress = 100
        progress.output_file = output_path
        progress.message = f"Download completed: {output_filename}"
        
    except Exception as e:
        progress.status = "failed"
        progress.error = str(e)
        progress.message = f"Download failed: {e}"
    finally:
        # Cleanup temp directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Failed to cleanup temp directory: {e}")

async def download_stream(url: str, temp_dir: str, filename: str) -> str:
    """Download a stream from URL with YouTube-specific headers"""
    output_path = os.path.join(temp_dir, filename)

    if not url:
        raise Exception(f"No URL provided for {filename}")

    # YouTube-specific headers to avoid 403 errors
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'identity',  # Don't use compression for video streams
        'Connection': 'keep-alive',
        'Range': 'bytes=0-',  # Request from beginning
        'Referer': 'https://www.youtube.com/',
        'Origin': 'https://www.youtube.com',
        'Sec-Fetch-Dest': 'video',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
    }

    print(f"[Download] Starting download: {filename}")
    print(f"[Download] URL: {url[:100]}...")

    try:
        response = requests.get(url, headers=headers, stream=True, timeout=60)
        print(f"[Download] Response status: {response.status_code}")

        if response.status_code == 403:
            print("[Download] Got 403, trying without Range header...")
            headers.pop('Range', None)
            response = requests.get(url, headers=headers, stream=True, timeout=60)

        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        if downloaded % (1024 * 1024) == 0:  # Log every MB
                            print(f"[Download] {filename}: {progress:.1f}% ({downloaded}/{total_size})")

        file_size = os.path.getsize(output_path)
        print(f"[Download] Completed: {filename} ({file_size} bytes)")

        if file_size == 0:
            raise Exception(f"Downloaded file is empty: {filename}")

        return output_path

    except Exception as e:
        print(f"[Download] Failed: {filename} - {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
        raise

async def merge_video_audio(video_path: str, audio_path: str, output_path: str):
    """Merge video and audio using FFmpeg"""
    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-i', audio_path,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-shortest',
        output_path
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        raise Exception(f"FFmpeg failed: {stderr.decode()}")

@router.post("/download", response_model=BrowserDownloadResponse)
async def start_browser_download(request: BrowserDownloadRequest, background_tasks: BackgroundTasks):
    """Start download using browser-extracted video info"""
    try:
        download_id = str(uuid.uuid4())
        
        # Generate filename
        if request.filename:
            filename = request.filename
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{request.video_info.title}_{timestamp}.mp4"
        
        # Clean filename
        filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        if not filename.endswith('.mp4'):
            filename += '.mp4'
        
        # Start download in background
        background_tasks.add_task(
            download_from_browser_info,
            download_id,
            request.video_info,
            request.selected_format_id,
            request.merge_audio,
            request.audio_format_id,
            filename
        )
        
        return BrowserDownloadResponse(
            download_id=download_id,
            filename=filename,
            status="started",
            message="Browser-assisted download started"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{download_id}")
async def get_browser_download_status(download_id: str):
    """Get download status"""
    if download_id not in active_downloads:
        raise HTTPException(status_code=404, detail="Download not found")
    
    progress = active_downloads[download_id]
    return {
        "download_id": download_id,
        "status": progress.status,
        "progress": progress.progress,
        "message": progress.message,
        "output_file": os.path.basename(progress.output_file) if progress.output_file else None,
        "error": progress.error
    }

@router.get("/downloads")
async def list_browser_downloads():
    """List all browser downloads"""
    downloads = []
    
    for download_id, progress in active_downloads.items():
        downloads.append({
            "download_id": download_id,
            "status": progress.status,
            "progress": progress.progress,
            "message": progress.message,
            "output_file": os.path.basename(progress.output_file) if progress.output_file else None,
        })
    
    return {"downloads": downloads}

@router.post("/extract/{video_id}")
async def extract_youtube_info(video_id: str):
    """Extract YouTube video info via server-side proxy to bypass CORS"""
    try:
        # Make request to YouTube's InnerTube API
        headers = {
            'Content-Type': 'application/json',
            'Origin': 'https://www.youtube.com',
            'Referer': 'https://www.youtube.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

        payload = {
            'context': INNERTUBE_CONTEXT,
            'videoId': video_id,
            'playbackContext': {
                'contentPlaybackContext': {
                    'html5Preference': 'HTML5_PREF_WANTS',
                },
            },
        }

        response = requests.post(
            f'https://www.youtube.com/youtubei/v1/player?key={INNERTUBE_API_KEY}',
            headers=headers,
            json=payload,
            timeout=30
        )

        if not response.ok:
            raise HTTPException(status_code=response.status_code, detail=f"YouTube API error: {response.status_code}")

        data = response.json()

        if not data.get('videoDetails'):
            raise HTTPException(status_code=404, detail="Video not found or unavailable")

        # Parse the response into our format
        video_info = parse_youtube_response(data)
        return video_info

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch video info: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

def parse_youtube_response(player_response: dict) -> dict:
    """Parse YouTube player response into our video info format"""
    video_details = player_response.get('videoDetails', {})
    streaming_data = player_response.get('streamingData', {})

    formats = []

    # Parse adaptive formats (video/audio separate)
    if streaming_data.get('adaptiveFormats'):
        for fmt in streaming_data['adaptiveFormats']:
            formats.append(parse_youtube_format(fmt, 'adaptive'))

    # Parse progressive formats (video+audio combined)
    if streaming_data.get('formats'):
        for fmt in streaming_data['formats']:
            formats.append(parse_youtube_format(fmt, 'progressive'))

    return {
        'id': video_details.get('videoId', ''),
        'title': video_details.get('title', 'Unknown'),
        'duration': int(video_details.get('lengthSeconds', 0)),
        'uploader': video_details.get('author', 'Unknown'),
        'thumbnail': video_details.get('thumbnail', {}).get('thumbnails', [{}])[0].get('url', ''),
        'formats': formats,
        'streamingData': streaming_data,
    }

def parse_youtube_format(fmt: dict, format_type: str) -> dict:
    """Parse a YouTube format into our format structure"""
    has_video = 'video' in fmt.get('mimeType', '')
    has_audio = 'audio' in fmt.get('mimeType', '')

    # Extract codec info
    mime_type = fmt.get('mimeType', '')
    codecs_match = re.search(r'codecs="([^"]+)"', mime_type)
    codecs = codecs_match.group(1).split(', ') if codecs_match else []

    vcodec = 'none'
    acodec = 'none'

    if has_video and codecs:
        vcodec = codecs[0]
    if has_audio:
        acodec = codecs[-1] if codecs else 'unknown'

    # Determine resolution
    resolution = 'audio only'
    if fmt.get('height') and fmt.get('width'):
        resolution = f"{fmt['width']}x{fmt['height']}"
    elif fmt.get('height'):
        resolution = f"{fmt['height']}p"

    # Get extension from mime type
    ext = 'unknown'
    if 'mp4' in mime_type:
        ext = 'mp4'
    elif 'webm' in mime_type:
        ext = 'webm'
    elif '3gpp' in mime_type:
        ext = '3gp'
    elif 'audio/mp4' in mime_type:
        ext = 'm4a'

    return {
        'format_id': str(fmt.get('itag', 'unknown')),
        'ext': ext,
        'resolution': resolution,
        'fps': fmt.get('fps', 0),
        'vcodec': vcodec,
        'acodec': acodec,
        'filesize': int(fmt.get('contentLength', 0)) if fmt.get('contentLength') else None,
        'url': fmt.get('url'),
        'has_video': has_video,
        'has_audio': has_audio,
        'format_note': f"{format_type} - {fmt.get('qualityLabel', fmt.get('audioQuality', 'unknown'))}",
        'quality': fmt.get('qualityLabel') or fmt.get('audioQuality'),
    }
