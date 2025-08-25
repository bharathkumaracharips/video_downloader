"""
M3U8 download API routes
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, Optional
import os
import asyncio
import threading
from datetime import datetime
import uuid
import re

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from m3u8 import download_m3u8_video

router = APIRouter()

# Store active downloads
active_downloads = {}

# Pydantic models
class M3U8DownloadRequest(BaseModel):
    url: HttpUrl
    filename: Optional[str] = None

class DownloadResponse(BaseModel):
    download_id: str
    filename: str
    status: str

class DownloadStatus(BaseModel):
    download_id: str
    status: str
    progress: float
    message: str
    output_file: Optional[str] = None
    error: Optional[str] = None

class DownloadProgress:
    def __init__(self, download_id):
        self.download_id = download_id
        self.status = "starting"
        self.progress = 0
        self.message = ""
        self.output_file = None
        self.error = None

    def update(self, data):
        """Update progress"""
        if data["type"] == "log":
            self.message = data["message"]
        elif data["type"] == "progress":
            self.progress = data["percentage"]

async def run_download(download_id: str, m3u8_url: str, output_path: str):
    """Run download in background"""
    progress_tracker = DownloadProgress(download_id)
    active_downloads[download_id] = progress_tracker

    try:
        progress_tracker.status = "downloading"
        result_path = await download_m3u8_video(
            m3u8_url,
            output_path,
            progress_callback=progress_tracker.update
        )

        progress_tracker.status = "completed"
        progress_tracker.output_file = result_path
        progress_tracker.progress = 100

    except Exception as e:
        progress_tracker.status = "failed"
        progress_tracker.error = str(e)

@router.post("/download", response_model=DownloadResponse)
async def start_m3u8_download(request: M3U8DownloadRequest, background_tasks: BackgroundTasks):
    """Start M3U8 download"""
    try:
        m3u8_url = str(request.url)
        custom_name = request.filename

        # Generate download ID and output filename
        download_id = str(uuid.uuid4())

        if custom_name:
            # Clean filename
            filename = re.sub(r'[^\w\-_\.]', '_', custom_name)
            if not filename.endswith('.mp4'):
                filename += '.mp4'
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"m3u8_download_{timestamp}.mp4"

        output_path = os.path.join('downloads', filename)
        os.makedirs('downloads', exist_ok=True)

        # Start download in background
        background_tasks.add_task(run_download, download_id, m3u8_url, output_path)

        return DownloadResponse(
            download_id=download_id,
            filename=filename,
            status='started'
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{download_id}", response_model=DownloadStatus)
async def get_download_status(download_id: str):
    """Get download status"""
    if download_id not in active_downloads:
        raise HTTPException(status_code=404, detail="Download not found")

    progress = active_downloads[download_id]
    return DownloadStatus(
        download_id=download_id,
        status=progress.status,
        progress=progress.progress,
        message=progress.message,
        output_file=os.path.basename(progress.output_file) if progress.output_file else None,
        error=progress.error
    )

@router.get("/download/{filename}")
async def download_file(filename: str):
    """Download completed file"""
    try:
        # Clean filename for security
        clean_filename = re.sub(r'[^\w\-_\.]', '_', filename)
        file_path = os.path.join('downloads', clean_filename)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")

        return FileResponse(
            path=file_path,
            filename=clean_filename,
            media_type='video/mp4'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/downloads")
async def list_downloads():
    """List all downloads"""
    downloads = []
    downloads_dir = 'downloads'

    if os.path.exists(downloads_dir):
        for filename in os.listdir(downloads_dir):
            if filename.endswith('.mp4'):
                file_path = os.path.join(downloads_dir, filename)
                stat = os.stat(file_path)
                downloads.append({
                    'filename': filename,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

    # Add active downloads
    for download_id, progress in active_downloads.items():
        if progress.status in ['downloading', 'starting']:
            downloads.append({
                'download_id': download_id,
                'status': progress.status,
                'progress': progress.progress,
                'message': progress.message
            })

    return {'downloads': downloads}
