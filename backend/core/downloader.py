"""
Advanced yt-dlp wrapper with enhanced features
"""

import yt_dlp
import asyncio
import os
import uuid
import re
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path
import json
import logging

from core.config import settings
from core.models import DownloadMode, DownloadStatus, DownloadProgress, VideoInfo, FormatInfo, FrameInfo, PlaylistInfo

logger = logging.getLogger(__name__)

def clean_filename(filename: str, max_length: int = 100) -> str:
    """Clean filename by removing special characters and limiting length"""
    # Remove or replace problematic characters
    cleaned = re.sub(r'[<>:"/\\|?*]', '', filename)
    cleaned = re.sub(r'[^\w\s-.]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Limit length
    if len(cleaned) > max_length:
        name, ext = os.path.splitext(cleaned)
        cleaned = name[:max_length-len(ext)] + ext
    
    return cleaned

class AdvancedDownloader:
    def __init__(self):
        self.active_downloads: Dict[str, Dict] = {}
        self.progress_callbacks: Dict[str, Callable] = {}
        
    def get_base_options(self) -> Dict[str, Any]:
        """Get base yt-dlp options"""
        return {
            'outtmpl': os.path.join(settings.DOWNLOAD_DIR, '%(title).100s.%(ext)s'),
            'restrictfilenames': True,
            'noplaylist': False,
            'ignoreerrors': True,
            'no_warnings': False,
            'extractaudio': False,
            'audioformat': 'mp3',
            'audioquality': '320',
            'embed_subs': False,  # Disable by default to avoid clutter
            'writesubtitles': False,
            'writeautomaticsub': False,
            'subtitleslangs': ['en'],
            'cachedir': settings.YTDLP_CACHE_DIR,
            'user_agent': settings.YTDLP_USER_AGENT,
            'http_headers': {
                'User-Agent': settings.YTDLP_USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            },
            'retries': 3,
            'fragment_retries': 10,
            'extractor_retries': 3,
            'socket_timeout': 30,
            # Video+Audio merging options
            'merge_output_format': 'mp4',
            'prefer_ffmpeg': True,
            'keepvideo': False,  # Don't keep separate video/audio files after merging
        }
    
    def create_progress_hook(self, download_id: str, callback: Optional[Callable] = None):
        """Create progress hook for yt-dlp"""
        def progress_hook(d):
            try:
                if d['status'] == 'downloading':
                    progress = 0.0
                    if d.get('total_bytes'):
                        progress = (d.get('downloaded_bytes', 0) / d['total_bytes']) * 100
                    elif d.get('total_bytes_estimate'):
                        progress = (d.get('downloaded_bytes', 0) / d['total_bytes_estimate']) * 100
                    
                    progress_data = {
                        'download_id': download_id,
                        'status': 'downloading',
                        'progress': progress,
                        'speed': d.get('_speed_str', ''),
                        'eta': d.get('_eta_str', ''),
                        'downloaded_bytes': d.get('downloaded_bytes'),
                        'total_bytes': d.get('total_bytes') or d.get('total_bytes_estimate'),
                        'filename': d.get('filename', ''),
                    }
                    
                    if callback:
                        callback(progress_data)
                        
                elif d['status'] == 'finished':
                    progress_data = {
                        'download_id': download_id,
                        'status': 'completed',
                        'progress': 100.0,
                        'filename': d.get('filename', ''),
                    }
                    
                    if callback:
                        callback(progress_data)
                        
            except Exception as e:
                logger.error(f"Progress hook error: {e}")
                
        return progress_hook
    
    async def get_video_info(self, url: str) -> VideoInfo:
        """Extract video information without downloading"""
        ydl_opts = self.get_base_options()
        ydl_opts.update({
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        })
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: ydl.extract_info(url, download=False)
                )
                
                if not info:
                    raise Exception("Failed to extract video information")
                
                # Process formats
                formats = []
                frames = []
                
                for f in info.get('formats', []):
                    format_info = FormatInfo(
                        format_id=f.get('format_id', ''),
                        ext=f.get('ext', ''),
                        resolution=f.get('resolution'),
                        fps=f.get('fps'),
                        vcodec=f.get('vcodec'),
                        acodec=f.get('acodec'),
                        filesize=f.get('filesize'),
                        filesize_approx=f.get('filesize_approx'),
                        tbr=f.get('tbr'),
                        vbr=f.get('vbr'),
                        abr=f.get('abr'),
                        format_note=f.get('format_note'),
                        quality=f.get('quality'),
                        has_video=f.get('vcodec', 'none') != 'none',
                        has_audio=f.get('acodec', 'none') != 'none'
                    )
                    formats.append(format_info)
                    
                    # Create frame info for video formats
                    if f.get('vcodec', 'none') != 'none' and f.get('resolution'):
                        filesize_mb = None
                        if f.get('filesize'):
                            filesize_mb = round(f.get('filesize') / (1024 * 1024), 1)
                        elif f.get('filesize_approx'):
                            filesize_mb = round(f.get('filesize_approx') / (1024 * 1024), 1)
                        
                        # Calculate quality score based on resolution and bitrate
                        quality_score = 0
                        if f.get('height'):
                            quality_score += f.get('height', 0) * 0.1
                        if f.get('tbr'):
                            quality_score += f.get('tbr', 0) * 0.01
                        
                        frame_info = FrameInfo(
                            format_id=f.get('format_id', ''),
                            resolution=f.get('resolution', 'Unknown'),
                            fps=f.get('fps'),
                            codec=f.get('vcodec', 'Unknown'),
                            container=f.get('ext', 'Unknown'),
                            bitrate=f.get('vbr') or f.get('tbr'),
                            filesize=f.get('filesize') or f.get('filesize_approx'),
                            filesize_mb=filesize_mb,
                            quality_score=quality_score,
                            has_audio=f.get('acodec', 'none') != 'none',
                            audio_codec=f.get('acodec') if f.get('acodec', 'none') != 'none' else None,
                            audio_bitrate=f.get('abr')
                        )
                        frames.append(frame_info)
                
                # Sort frames by quality score (highest first)
                frames.sort(key=lambda x: x.quality_score or 0, reverse=True)
                
                return VideoInfo(
                    id=info.get('id', ''),
                    title=info.get('title', ''),
                    description=info.get('description'),
                    uploader=info.get('uploader'),
                    upload_date=info.get('upload_date'),
                    duration=info.get('duration'),
                    view_count=info.get('view_count'),
                    like_count=info.get('like_count'),
                    thumbnail=info.get('thumbnail'),
                    formats=formats,
                    frames=frames,
                    subtitles=info.get('subtitles'),
                    is_live=info.get('is_live', False),
                    live_status=info.get('live_status')
                )
                
        except Exception as e:
            logger.error(f"Error extracting video info: {e}")
            raise Exception(f"Failed to get video information: {str(e)}")
    
    async def get_playlist_info(self, url: str) -> PlaylistInfo:
        """Extract playlist information"""
        ydl_opts = self.get_base_options()
        ydl_opts.update({
            'quiet': True,
            'extract_flat': True,
            'skip_download': True,
        })
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: ydl.extract_info(url, download=False)
                )
                
                if not info:
                    raise Exception("Failed to extract playlist information")
                
                videos = []
                for idx, entry in enumerate(info.get('entries', []), 1):
                    if entry:
                        videos.append({
                            'id': entry.get('id', ''),
                            'title': entry.get('title', f'Video {idx}'),
                            'duration': entry.get('duration'),
                            'uploader': entry.get('uploader'),
                            'index': idx
                        })
                
                return PlaylistInfo(
                    id=info.get('id', ''),
                    title=info.get('title', ''),
                    description=info.get('description'),
                    uploader=info.get('uploader'),
                    video_count=len(videos),
                    videos=videos
                )
                
        except Exception as e:
            logger.error(f"Error extracting playlist info: {e}")
            raise Exception(f"Failed to get playlist information: {str(e)}")
    
    async def download_video(self, url: str, options: Dict[str, Any], 
                           progress_callback: Optional[Callable] = None) -> str:
        """Download video with custom options"""
        download_id = str(uuid.uuid4())
        
        ydl_opts = self.get_base_options()
        ydl_opts.update(options)
        ydl_opts['progress_hooks'] = [self.create_progress_hook(download_id, progress_callback)]
        
        try:
            self.active_downloads[download_id] = {
                'status': DownloadStatus.DOWNLOADING,
                'url': url,
                'options': options
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: ydl.extract_info(url, download=True)
                )
                
                if not info:
                    raise Exception("Download failed - no info returned")
                
                filename = ydl.prepare_filename(info)
                
                # Handle merged output filename
                if 'merge_output_format' in ydl_opts and ydl_opts['merge_output_format']:
                    # yt-dlp automatically merges and creates the final file
                    base_name = os.path.splitext(filename)[0]
                    merged_filename = f"{base_name}.{ydl_opts['merge_output_format']}"
                    if os.path.exists(merged_filename):
                        filename = merged_filename
                
                self.active_downloads[download_id]['status'] = DownloadStatus.COMPLETED
                self.active_downloads[download_id]['filename'] = filename
                
                return filename
                
        except Exception as e:
            logger.error(f"Download error: {e}")
            self.active_downloads[download_id]['status'] = DownloadStatus.FAILED
            self.active_downloads[download_id]['error'] = str(e)
            raise Exception(f"Download failed: {str(e)}")
    
    async def download_video_with_merge(self, url: str, quality: str = "best", 
                                      progress_callback: Optional[Callable] = None) -> str:
        """Download video with automatic video+audio merging for high quality"""
        download_id = str(uuid.uuid4())
        
        # Determine format selector based on quality
        if quality == "best":
            format_selector = "bestvideo+bestaudio/best"
        elif "height<=" in quality:
            height = quality.split("<=")[1].rstrip("]")
            format_selector = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
        else:
            format_selector = quality
        
        ydl_opts = self.get_base_options()
        ydl_opts.update({
            'format': format_selector,
            'merge_output_format': 'mp4',
            'prefer_ffmpeg': True,
            'keepvideo': False,  # Don't keep separate files
            'outtmpl': os.path.join(settings.DOWNLOAD_DIR, '%(title).100s.%(ext)s'),
            'restrictfilenames': True,
            'windowsfilenames': True,  # Ensure Windows compatibility
        })
        ydl_opts['progress_hooks'] = [self.create_progress_hook(download_id, progress_callback)]
        
        try:
            self.active_downloads[download_id] = {
                'status': DownloadStatus.DOWNLOADING,
                'url': url,
                'format': format_selector
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: ydl.extract_info(url, download=True)
                )
                
                if not info:
                    raise Exception("Download failed - no info returned")
                
                # Get the final merged filename
                filename = ydl.prepare_filename(info)
                base_name = os.path.splitext(filename)[0]
                final_filename = f"{base_name}.mp4"
                
                # Check if merged file exists
                if os.path.exists(final_filename):
                    filename = final_filename
                elif os.path.exists(filename):
                    # File might already be in correct format
                    pass
                else:
                    raise Exception("Merged file not found after download")
                
                self.active_downloads[download_id]['status'] = DownloadStatus.COMPLETED
                self.active_downloads[download_id]['filename'] = filename
                
                return filename
                
        except Exception as e:
            logger.error(f"Video merge download error: {e}")
            self.active_downloads[download_id]['status'] = DownloadStatus.FAILED
            self.active_downloads[download_id]['error'] = str(e)
            raise Exception(f"Video download with merge failed: {str(e)}")
    
    def get_download_status(self, download_id: str) -> Optional[Dict]:
        """Get download status by ID"""
        return self.active_downloads.get(download_id)
    
    async def download_frame_with_audio(self, url: str, video_format_id: str, 
                                      audio_format_id: Optional[str] = None,
                                      progress_callback: Optional[Callable] = None) -> str:
        """Download specific video frame and merge with best audio"""
        download_id = str(uuid.uuid4())
        
        # If no audio format specified, use best audio
        if audio_format_id:
            format_selector = f"{video_format_id}+{audio_format_id}"
        else:
            format_selector = f"{video_format_id}+bestaudio"
        
        ydl_opts = self.get_base_options()
        ydl_opts.update({
            'format': format_selector,
            'merge_output_format': 'mp4',
            'prefer_ffmpeg': True,
            'keepvideo': False,
            'outtmpl': os.path.join(settings.DOWNLOAD_DIR, '%(title).100s.%(ext)s'),
            'restrictfilenames': True,
            'windowsfilenames': True,
        })
        ydl_opts['progress_hooks'] = [self.create_progress_hook(download_id, progress_callback)]
        
        try:
            self.active_downloads[download_id] = {
                'status': DownloadStatus.DOWNLOADING,
                'url': url,
                'format': format_selector
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: ydl.extract_info(url, download=True)
                )
                
                if not info:
                    raise Exception("Download failed - no info returned")
                
                # Get the final merged filename
                filename = ydl.prepare_filename(info)
                base_name = os.path.splitext(filename)[0]
                final_filename = f"{base_name}.mp4"
                
                # Check if merged file exists
                if os.path.exists(final_filename):
                    filename = final_filename
                elif os.path.exists(filename):
                    pass
                else:
                    raise Exception("Merged file not found after download")
                
                self.active_downloads[download_id]['status'] = DownloadStatus.COMPLETED
                self.active_downloads[download_id]['filename'] = filename
                
                return filename
                
        except Exception as e:
            logger.error(f"Frame download error: {e}")
            self.active_downloads[download_id]['status'] = DownloadStatus.FAILED
            self.active_downloads[download_id]['error'] = str(e)
            raise Exception(f"Frame download failed: {str(e)}")

    def cancel_download(self, download_id: str) -> bool:
        """Cancel active download"""
        if download_id in self.active_downloads:
            self.active_downloads[download_id]['status'] = DownloadStatus.CANCELLED
            return True
        return False

# Global downloader instance
downloader = AdvancedDownloader()