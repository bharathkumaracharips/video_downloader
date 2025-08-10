"""
Download queue management service
"""

import asyncio
import uuid
from typing import Dict, List, Optional
from datetime import datetime
import logging

from core.models import DownloadStatus, DownloadProgress
from core.config import settings
from core.downloader import downloader

logger = logging.getLogger(__name__)

class QueueManager:
    def __init__(self):
        self.queue: List[Dict] = []
        self.active_downloads: Dict[str, Dict] = {}
        self.completed_downloads: Dict[str, Dict] = {}
        self.failed_downloads: Dict[str, Dict] = {}
        self.max_concurrent = settings.MAX_CONCURRENT_DOWNLOADS
        self.is_processing = False
        
    async def add_to_queue(self, download_request: Dict) -> str:
        """Add download request to queue"""
        download_id = str(uuid.uuid4())
        
        queue_item = {
            'download_id': download_id,
            'request': download_request,
            'status': DownloadStatus.PENDING,
            'created_at': datetime.now(),
            'priority': download_request.get('priority', 0)
        }
        
        # Insert based on priority (higher priority first)
        inserted = False
        for i, item in enumerate(self.queue):
            if queue_item['priority'] > item['priority']:
                self.queue.insert(i, queue_item)
                inserted = True
                break
        
        if not inserted:
            self.queue.append(queue_item)
        
        logger.info(f"Added download {download_id} to queue")
        
        # Start processing if not already running
        if not self.is_processing:
            asyncio.create_task(self.process_queue())
        
        return download_id
    
    async def process_queue(self):
        """Process download queue"""
        if self.is_processing:
            return
            
        self.is_processing = True
        logger.info("Started queue processing")
        
        try:
            while self.queue or self.active_downloads:
                # Start new downloads if we have capacity
                while (len(self.active_downloads) < self.max_concurrent and 
                       self.queue):
                    
                    queue_item = self.queue.pop(0)
                    download_id = queue_item['download_id']
                    
                    # Start download
                    task = asyncio.create_task(
                        self._process_download(download_id, queue_item['request'])
                    )
                    
                    self.active_downloads[download_id] = {
                        'task': task,
                        'request': queue_item['request'],
                        'started_at': datetime.now()
                    }
                    
                    logger.info(f"Started download {download_id}")
                
                # Wait a bit before checking again
                await asyncio.sleep(1)
                
                # Clean up completed tasks
                completed_ids = []
                for download_id, download_info in self.active_downloads.items():
                    if download_info['task'].done():
                        completed_ids.append(download_id)
                
                for download_id in completed_ids:
                    download_info = self.active_downloads.pop(download_id)
                    try:
                        result = await download_info['task']
                        self.completed_downloads[download_id] = {
                            'result': result,
                            'completed_at': datetime.now()
                        }
                        logger.info(f"Download {download_id} completed successfully")
                    except Exception as e:
                        self.failed_downloads[download_id] = {
                            'error': str(e),
                            'failed_at': datetime.now()
                        }
                        logger.error(f"Download {download_id} failed: {e}")
        
        finally:
            self.is_processing = False
            logger.info("Queue processing stopped")
    
    async def _process_download(self, download_id: str, request: Dict):
        """Process individual download"""
        try:
            download_type = request.get('type')
            url = request.get('url')
            options = request.get('options', {})
            
            # Create progress callback
            def progress_callback(progress_data):
                # You can emit this to WebSocket clients or store in database
                logger.debug(f"Download {download_id} progress: {progress_data['progress']:.1f}%")
            
            # Perform download based on type
            if download_type == 'video':
                filename = await downloader.download_video(url, options, progress_callback)
            elif download_type == 'video_merge':
                # Use the new merge method for high-quality video downloads
                quality = options.get('format', 'best')
                filename = await downloader.download_video_with_merge(url, quality, progress_callback)
            elif download_type == 'audio':
                filename = await downloader.download_video(url, options, progress_callback)
            elif download_type == 'playlist_video':
                filename = await downloader.download_video(url, options, progress_callback)
            elif download_type == 'playlist_audio':
                filename = await downloader.download_video(url, options, progress_callback)
            elif download_type == 'live':
                filename = await downloader.download_video(url, options, progress_callback)
            else:
                raise ValueError(f"Unknown download type: {download_type}")
            
            return {
                'download_id': download_id,
                'filename': filename,
                'status': 'completed'
            }
            
        except Exception as e:
            logger.error(f"Download {download_id} failed: {e}")
            raise
    
    def get_queue_status(self) -> Dict:
        """Get current queue status"""
        return {
            'total_items': len(self.queue) + len(self.active_downloads),
            'pending_items': len(self.queue),
            'active_downloads': len(self.active_downloads),
            'completed_items': len(self.completed_downloads),
            'failed_items': len(self.failed_downloads)
        }
    
    def get_download_status(self, download_id: str) -> Optional[Dict]:
        """Get status of specific download"""
        # Check active downloads
        if download_id in self.active_downloads:
            return {
                'status': DownloadStatus.DOWNLOADING,
                'started_at': self.active_downloads[download_id]['started_at']
            }
        
        # Check completed downloads
        if download_id in self.completed_downloads:
            return {
                'status': DownloadStatus.COMPLETED,
                'result': self.completed_downloads[download_id]['result'],
                'completed_at': self.completed_downloads[download_id]['completed_at']
            }
        
        # Check failed downloads
        if download_id in self.failed_downloads:
            return {
                'status': DownloadStatus.FAILED,
                'error': self.failed_downloads[download_id]['error'],
                'failed_at': self.failed_downloads[download_id]['failed_at']
            }
        
        # Check queue
        for item in self.queue:
            if item['download_id'] == download_id:
                return {
                    'status': DownloadStatus.PENDING,
                    'created_at': item['created_at']
                }
        
        return None
    
    def cancel_download(self, download_id: str) -> bool:
        """Cancel download"""
        # Remove from queue
        self.queue = [item for item in self.queue if item['download_id'] != download_id]
        
        # Cancel active download
        if download_id in self.active_downloads:
            task = self.active_downloads[download_id]['task']
            task.cancel()
            self.active_downloads.pop(download_id)
            return True
        
        return False

# Global queue manager instance
queue_manager = QueueManager()