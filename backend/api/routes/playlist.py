"""
Playlist download API routes
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import os
import json
import asyncio
import logging
from typing import AsyncGenerator

from core.models import PlaylistDownloadRequest, DownloadResponse, URLRequest, PlaylistInfo
from core.downloader import downloader
from services.queue_manager import queue_manager
from core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/info", response_model=PlaylistInfo)
async def get_playlist_info(request: URLRequest):
    """Get playlist information"""
    try:
        info = await downloader.get_playlist_info(str(request.url))
        return info
    except Exception as e:
        logger.error(f"Error getting playlist info: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/download", response_model=DownloadResponse)
async def download_playlist(request: PlaylistDownloadRequest):
    """Download entire playlist or selected videos"""
    try:
        # Prepare download options based on mode
        if request.mode == "audio":
            options = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': request.audio_format,
                    'preferredquality': request.audio_quality if request.audio_quality != 'best' else '320',
                }],
                'outtmpl': os.path.join(
                    settings.DOWNLOAD_DIR, 
                    'playlist',
                    '%(playlist_index)s - %(title).80s.%(ext)s'
                ),
                'restrictfilenames': True,
                'windowsfilenames': True,
            }
        else:
            # For video, use merge format for high quality
            format_selector = "bestvideo+bestaudio/best" if request.quality.value == "best" else f"bestvideo[height<={request.quality.value.split('<=')[1].rstrip(']')}]+bestaudio/best" if "height<=" in request.quality.value else request.quality.value
            options = {
                'format': format_selector,
                'merge_output_format': 'mp4',
                'outtmpl': os.path.join(
                    settings.DOWNLOAD_DIR, 
                    'playlist',
                    '%(playlist_index)s - %(title).80s.%(ext)s'
                ),
                'restrictfilenames': True,
                'windowsfilenames': True,
            }
        
        # Handle video selection
        if request.video_ids:
            # Download specific videos
            playlist_url = str(request.url)
            for video_id in request.video_ids:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                download_request = {
                    'type': request.mode,
                    'url': video_url,
                    'options': options.copy(),
                    'priority': 0
                }
                await queue_manager.add_to_queue(download_request)
        else:
            # Download entire playlist
            if request.start_index or request.end_index:
                options['playliststart'] = request.start_index or 1
                if request.end_index:
                    options['playlistend'] = request.end_index
            
            download_request = {
                'type': f'playlist_{request.mode}',
                'url': str(request.url),
                'options': options,
                'priority': 0
            }
            await queue_manager.add_to_queue(download_request)
        
        return DownloadResponse(
            download_id="playlist",
            status="pending",
            message=f"Playlist {request.mode} download added to queue"
        )
        
    except Exception as e:
        logger.error(f"Error starting playlist download: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/stream")
async def download_playlist_stream(url: str, mode: str = "audio", format: str = "mp3"):
    """Stream playlist download progress"""
    
    async def generate_progress() -> AsyncGenerator[str, None]:
        try:
            # Get playlist info first
            playlist_info = await downloader.get_playlist_info(url)
            
            yield f"data: {json.dumps({'type': 'info', 'data': {'total': playlist_info.video_count, 'title': playlist_info.title}})}\n\n"
            
            # Prepare download options
            if mode == "audio":
                options = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': format,
                        'preferredquality': '320',
                    }],
                    'outtmpl': os.path.join(
                        settings.DOWNLOAD_DIR, 
                        'playlist',
                        '%(playlist_index)s - %(title)s.%(ext)s'
                    ),
                    'ignoreerrors': True,
                }
            else:
                options = {
                    'format': 'best',
                    'outtmpl': os.path.join(
                        settings.DOWNLOAD_DIR, 
                        'playlist',
                        '%(playlist_index)s - %(title)s.%(ext)s'
                    ),
                    'ignoreerrors': True,
                }
            
            downloaded_count = 0
            failed_count = 0
            
            # Download each video
            for video in playlist_info.videos:
                try:
                    video_url = f"https://www.youtube.com/watch?v={video['id']}"
                    
                    # Progress callback for individual video
                    def progress_callback(progress_data):
                        pass  # Individual video progress can be handled here
                    
                    filename = await downloader.download_video(video_url, options, progress_callback)
                    downloaded_count += 1
                    
                    yield f"data: {json.dumps({'type': 'progress', 'data': {'current': downloaded_count, 'total': playlist_info.video_count, 'filename': os.path.basename(filename), 'status': 'success'}})}\n\n"
                    
                except Exception as e:
                    failed_count += 1
                    error_msg = f"Failed: {video['title']} - {str(e)}"
                    
                    yield f"data: {json.dumps({'type': 'progress', 'data': {'current': downloaded_count + failed_count, 'total': playlist_info.video_count, 'filename': error_msg, 'status': 'error'}})}\n\n"
                
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.1)
            
            # Send completion
            yield f"data: {json.dumps({'type': 'complete', 'data': {'downloaded': downloaded_count, 'failed': failed_count, 'total': playlist_info.video_count}})}\n\n"
            
        except Exception as e:
            logger.error(f"Playlist download stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"
    
    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

@router.post("/download/batch")
async def download_playlist_batch(request: PlaylistDownloadRequest):
    """Download playlist in batches for better performance"""
    try:
        playlist_info = await downloader.get_playlist_info(str(request.url))
        
        # Determine which videos to download
        videos_to_download = playlist_info.videos
        if request.video_ids:
            videos_to_download = [v for v in playlist_info.videos if v['id'] in request.video_ids]
        elif request.start_index or request.end_index:
            start = (request.start_index or 1) - 1
            end = request.end_index or len(playlist_info.videos)
            videos_to_download = playlist_info.videos[start:end]
        
        # Add each video to queue with batch priority
        download_ids = []
        for i, video in enumerate(videos_to_download):
            video_url = f"https://www.youtube.com/watch?v={video['id']}"
            
            if request.mode == "audio":
                options = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': request.audio_format,
                        'preferredquality': request.audio_quality if request.audio_quality != 'best' else '320',
                    }],
                    'outtmpl': os.path.join(
                        settings.DOWNLOAD_DIR, 
                        'playlist',
                        f'{i+1:03d} - %(title)s.%(ext)s'
                    ),
                }
            else:
                options = {
                    'format': request.quality.value,
                    'outtmpl': os.path.join(
                        settings.DOWNLOAD_DIR, 
                        'playlist',
                        f'{i+1:03d} - %(title)s.%(ext)s'
                    ),
                }
            
            download_request = {
                'type': request.mode,
                'url': video_url,
                'options': options,
                'priority': 0,
                'batch_id': f"playlist_{playlist_info.id}",
                'batch_index': i
            }
            
            download_id = await queue_manager.add_to_queue(download_request)
            download_ids.append(download_id)
        
        return {
            "message": f"Added {len(videos_to_download)} videos to download queue",
            "download_ids": download_ids,
            "total_videos": len(videos_to_download),
            "playlist_title": playlist_info.title
        }
        
    except Exception as e:
        logger.error(f"Error starting batch playlist download: {e}")
        raise HTTPException(status_code=500, detail=str(e))