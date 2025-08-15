"""
Advanced yt-dlp wrapper with enhanced features
"""

import yt_dlp
import asyncio
import os
import uuid
import re
import subprocess
import signal
import time
import gc
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path
import json
import logging

from core.config import settings
from core.models import DownloadMode, DownloadStatus, DownloadProgress, VideoInfo, FormatInfo, FrameInfo, PlaylistInfo, SponsorBlockMusicRequest

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
        self.ffmpeg_processes: Dict[str, subprocess.Popen] = {}
        self.max_concurrent_downloads = 2  # Limit concurrent downloads
        
    def get_base_options(self) -> Dict[str, Any]:
        """Get base yt-dlp options - simplified for better compatibility"""
        return {
            'outtmpl': os.path.join(settings.DOWNLOAD_DIR, '%(title).100s.%(ext)s'),
            'restrictfilenames': True,
            'noplaylist': False,
            'ignoreerrors': True,
            'no_warnings': False,
            'cachedir': settings.YTDLP_CACHE_DIR,
            # Basic retries
            'retries': 3,
            'fragment_retries': 5,
            'extractor_retries': 2,
            'socket_timeout': 30,
            # Video+Audio merging options
            'merge_output_format': 'mp4',
            'prefer_ffmpeg': True,
            'keepvideo': False,
            # Memory management
            'concurrent_fragment_downloads': 1,
            'buffersize': 1024 * 1024,  # 1MB buffer size
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
        """Extract video information without downloading with multiple fallback strategies"""
        # Try multiple extraction strategies - simplified
        strategies = [
            # Strategy 1: Basic extraction
            {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            },
            # Strategy 2: With android client
            {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android'],
                    }
                },
            },
            # Strategy 3: With web client
            {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['web'],
                    }
                },
            }
        ]
        
        last_error = None
        
        for i, strategy in enumerate(strategies):
            try:
                ydl_opts = self.get_base_options()
                ydl_opts.update(strategy)
                
                logger.info(f"Trying extraction strategy {i+1}/3 for URL: {url}")
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: ydl.extract_info(url, download=False)
                    )
                    
                    if not info:
                        raise Exception("Failed to extract video information")
                    
                    logger.info(f"Successfully extracted info using strategy {i+1}")
                    break
                    
            except Exception as e:
                last_error = e
                logger.warning(f"Strategy {i+1} failed: {str(e)}")
                if i < len(strategies) - 1:
                    continue
                else:
                    # All strategies failed
                    error_msg = f"All extraction strategies failed. Last error: {str(last_error)}"
                    if "Failed to extract any player response" in str(last_error):
                        error_msg += "\n\nThis is likely due to YouTube changes. Try updating yt-dlp with: pip install --upgrade yt-dlp"
                    raise Exception(error_msg)
        
        try:
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
        """Download video with automatic video+audio merging for high quality - crash-safe version"""
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
            # Additional crash prevention options
            'writeinfojson': False,  # Don't write info files to save space
            'writethumbnail': False,  # Don't download thumbnails
            'writesubtitles': False,  # Don't download subtitles unless requested
            # FFmpeg-specific options for stability
            'postprocessor_args': {
                'ffmpeg': [
                    '-threads', '2',  # Limit threads to prevent CPU overload
                    '-preset', 'fast',  # Fast encoding preset
                    '-crf', '23',  # Reasonable quality/size balance
                    '-maxrate', '10M',  # Limit bitrate to prevent memory issues
                    '-bufsize', '20M',  # Buffer size for rate control
                    '-movflags', '+faststart',  # Optimize for streaming
                    '-avoid_negative_ts', 'make_zero',  # Fix timestamp issues
                    '-max_muxing_queue_size', '1024',  # Limit muxing queue
                    '-fflags', '+genpts+igndts',  # Generate PTS and ignore DTS
                ]
            },
        })
        ydl_opts['progress_hooks'] = [self.create_progress_hook(download_id, progress_callback)]
        
        try:
            # Check system resources before starting
            if not self._check_system_resources():
                raise Exception("Insufficient system resources for download")
            
            # Clean up any hanging processes
            self._cleanup_processes()
            
            self.active_downloads[download_id] = {
                'status': DownloadStatus.DOWNLOADING,
                'url': url,
                'format': format_selector,
                'start_time': time.time()
            }
            
            # Use a timeout for the download operation
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # Set a reasonable timeout for large downloads (30 minutes)
                    info = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, lambda: ydl.extract_info(url, download=True)
                        ),
                        timeout=1800  # 30 minutes timeout
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
                    
                    # Verify file is not corrupted
                    if os.path.getsize(filename) < 1024:  # Less than 1KB
                        raise Exception("Downloaded file appears to be corrupted (too small)")
                    
                    self.active_downloads[download_id]['status'] = DownloadStatus.COMPLETED
                    self.active_downloads[download_id]['filename'] = filename
                    
                    # Clean up after successful download
                    self._cleanup_processes()
                    
                    return filename
                    
            except asyncio.TimeoutError:
                raise Exception("Download timed out after 30 minutes")
                
        except Exception as e:
            logger.error(f"Video merge download error: {e}")
            self.active_downloads[download_id]['status'] = DownloadStatus.FAILED
            self.active_downloads[download_id]['error'] = str(e)
            
            # Clean up on error
            self._cleanup_processes()
            
            raise Exception(f"Video download with merge failed: {str(e)}")
    
    def get_download_status(self, download_id: str) -> Optional[Dict]:
        """Get download status by ID"""
        return self.active_downloads.get(download_id)
    
    async def download_frame_with_audio(self, url: str, video_format_id: str, 
                                      audio_format_id: Optional[str] = None,
                                      progress_callback: Optional[Callable] = None) -> str:
        """Download specific video frame and merge with best audio - crash-safe version"""
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
            # Memory and stability optimizations
            'writeinfojson': False,
            'writethumbnail': False,
            'concurrent_fragment_downloads': 1,  # Single thread for stability
            # Safe FFmpeg options
            'postprocessor_args': {
                'ffmpeg': [
                    '-threads', '1',  # Single thread for frame downloads
                    '-preset', 'ultrafast',  # Fastest preset for single frames
                    '-avoid_negative_ts', 'make_zero',
                    '-max_muxing_queue_size', '512',  # Smaller queue for frames
                    '-movflags', '+faststart',
                ]
            },
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

    def _cleanup_processes(self):
        """Clean up any hanging FFmpeg processes"""
        try:
            # Clean up tracked processes
            for download_id, process in list(self.ffmpeg_processes.items()):
                if process.poll() is not None:  # Process has finished
                    del self.ffmpeg_processes[download_id]
                elif time.time() - process.creation_time > 3600:  # Process running > 1 hour
                    logger.warning(f"Terminating long-running FFmpeg process for {download_id}")
                    process.terminate()
                    time.sleep(2)
                    if process.poll() is None:
                        process.kill()
                    del self.ffmpeg_processes[download_id]
            
            # Force garbage collection
            gc.collect()
            
        except Exception as e:
            logger.error(f"Error cleaning up processes: {e}")
    
    def _check_system_resources(self) -> bool:
        """Check if system has enough resources for download"""
        try:
            # Check available memory (require at least 500MB free)
            memory = os.popen('free -m').read() if os.name != 'nt' else None
            if memory:
                lines = memory.strip().split('\n')
                if len(lines) > 1:
                    available = int(lines[1].split()[6])  # Available memory
                    if available < 500:  # Less than 500MB
                        logger.warning(f"Low memory: {available}MB available")
                        return False
            
            # Check active downloads count
            active_count = sum(1 for d in self.active_downloads.values() 
                             if d.get('status') == DownloadStatus.DOWNLOADING)
            if active_count >= self.max_concurrent_downloads:
                logger.warning(f"Too many active downloads: {active_count}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking system resources: {e}")
            return True  # Allow download if check fails
    
    async def download_music_with_sponsorblock(self, url: str, quality: str = "best", 
                                             audio_format: str = "mp3", 
                                             remove_categories: List[str] = None,
                                             mark_categories: List[str] = None,
                                             sponsorblock_api: str = "https://sponsor.ajay.app",
                                             progress_callback: Optional[Callable] = None) -> str:
        """Download music with SponsorBlock integration to remove unwanted segments"""
        download_id = str(uuid.uuid4())
        
        if remove_categories is None:
            remove_categories = ["sponsor", "intro", "outro", "selfpromo", "preview", "interaction", "music_offtopic"]
        
        if mark_categories is None:
            mark_categories = []
        
        ydl_opts = self.get_base_options()
        
        # SponsorBlock configuration
        sponsorblock_opts = {}
        
        if remove_categories:
            sponsorblock_opts['sponsorblock_remove'] = ','.join(remove_categories)
            
        if mark_categories:
            sponsorblock_opts['sponsorblock_mark'] = ','.join(mark_categories)
            
        if sponsorblock_api != "https://sponsor.ajay.app":
            sponsorblock_opts['sponsorblock_api'] = sponsorblock_api
        
        # Audio extraction post-processor
        postprocessors = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': audio_format,
            'preferredquality': quality if quality != 'best' else '320',
        }]
        
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': postprocessors,
            'outtmpl': os.path.join(settings.DOWNLOAD_DIR, '%(title).100s.%(ext)s'),
            'restrictfilenames': True,
            'windowsfilenames': True,
            **sponsorblock_opts  # Add SponsorBlock options
        })
        ydl_opts['progress_hooks'] = [self.create_progress_hook(download_id, progress_callback)]
        
        try:
            # Check system resources before starting
            if not self._check_system_resources():
                raise Exception("Insufficient system resources for download")
            
            # Clean up any hanging processes
            self._cleanup_processes()
            
            self.active_downloads[download_id] = {
                'status': DownloadStatus.DOWNLOADING,
                'url': url,
                'type': 'music_sponsorblock',
                'start_time': time.time()
            }
            
            # Use timeout for the download operation
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, lambda: ydl.extract_info(url, download=True)
                        ),
                        timeout=1800  # 30 minutes timeout
                    )
                    
                    if not info:
                        raise Exception("Download failed - no info returned")
                    
                    # Get the final processed filename
                    filename = ydl.prepare_filename(info)
                    base_name = os.path.splitext(filename)[0]
                    final_filename = f"{base_name}.{audio_format}"
                    
                    # Check if processed file exists
                    if os.path.exists(final_filename):
                        filename = final_filename
                    elif os.path.exists(filename):
                        pass
                    else:
                        raise Exception("Processed music file not found after download")
                    
                    # Verify file is not corrupted
                    if os.path.getsize(filename) < 1024:  # Less than 1KB
                        raise Exception("Downloaded file appears to be corrupted (too small)")
                    
                    self.active_downloads[download_id]['status'] = DownloadStatus.COMPLETED
                    self.active_downloads[download_id]['filename'] = filename
                    
                    # Clean up after successful download
                    self._cleanup_processes()
                    
                    logger.info(f"SponsorBlock music download completed: {filename}")
                    logger.info(f"Removed categories: {remove_categories}")
                    if mark_categories:
                        logger.info(f"Marked categories: {mark_categories}")
                    
                    return filename
                    
            except asyncio.TimeoutError:
                raise Exception("Download timed out after 30 minutes")
                
        except Exception as e:
            logger.error(f"SponsorBlock music download error: {e}")
            self.active_downloads[download_id]['status'] = DownloadStatus.FAILED
            self.active_downloads[download_id]['error'] = str(e)
            
            # Clean up on error
            self._cleanup_processes()
            
            raise Exception(f"SponsorBlock music download failed: {str(e)}")
    
    def cancel_download(self, download_id: str) -> bool:
        """Cancel active download and clean up resources"""
        if download_id in self.active_downloads:
            self.active_downloads[download_id]['status'] = DownloadStatus.CANCELLED
            
            # Clean up any associated FFmpeg process
            if download_id in self.ffmpeg_processes:
                try:
                    process = self.ffmpeg_processes[download_id]
                    process.terminate()
                    time.sleep(1)
                    if process.poll() is None:
                        process.kill()
                    del self.ffmpeg_processes[download_id]
                except Exception as e:
                    logger.error(f"Error terminating process for {download_id}: {e}")
            
            return True
        return False

# Global downloader instance
downloader = AdvancedDownloader()