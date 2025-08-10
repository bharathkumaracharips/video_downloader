"""
Download queue management API routes
"""

from fastapi import APIRouter, HTTPException
import logging

from core.models import QueueStatus, DownloadStatus
from services.queue_manager import queue_manager

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/status", response_model=QueueStatus)
async def get_queue_status():
    """Get current queue status"""
    try:
        status = queue_manager.get_queue_status()
        return QueueStatus(**status)
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/downloads")
async def get_all_downloads():
    """Get status of all downloads"""
    try:
        # Get queue items
        queue_items = [
            {
                "download_id": item['download_id'],
                "status": "pending",
                "created_at": item['created_at'],
                "url": item['request'].get('url'),
                "type": item['request'].get('type')
            }
            for item in queue_manager.queue
        ]
        
        # Get active downloads
        active_downloads = [
            {
                "download_id": download_id,
                "status": "downloading",
                "started_at": info['started_at'],
                "url": info['request'].get('url'),
                "type": info['request'].get('type')
            }
            for download_id, info in queue_manager.active_downloads.items()
        ]
        
        # Get completed downloads
        completed_downloads = [
            {
                "download_id": download_id,
                "status": "completed",
                "completed_at": info['completed_at'],
                "result": info['result']
            }
            for download_id, info in queue_manager.completed_downloads.items()
        ]
        
        # Get failed downloads
        failed_downloads = [
            {
                "download_id": download_id,
                "status": "failed",
                "failed_at": info['failed_at'],
                "error": info['error']
            }
            for download_id, info in queue_manager.failed_downloads.items()
        ]
        
        return {
            "queue": queue_items,
            "active": active_downloads,
            "completed": completed_downloads,
            "failed": failed_downloads,
            "summary": queue_manager.get_queue_status()
        }
        
    except Exception as e:
        logger.error(f"Error getting all downloads: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{download_id}")
async def get_download_status(download_id: str):
    """Get status of specific download"""
    try:
        status = queue_manager.get_download_status(download_id)
        if not status:
            raise HTTPException(status_code=404, detail="Download not found")
        
        return {
            "download_id": download_id,
            **status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting download status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/download/{download_id}")
async def cancel_download(download_id: str):
    """Cancel a download"""
    try:
        success = queue_manager.cancel_download(download_id)
        if not success:
            raise HTTPException(status_code=404, detail="Download not found or cannot be cancelled")
        
        return {
            "message": f"Download {download_id} cancelled successfully",
            "download_id": download_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling download: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear")
async def clear_queue():
    """Clear completed and failed downloads from queue"""
    try:
        # Clear completed and failed downloads
        cleared_completed = len(queue_manager.completed_downloads)
        cleared_failed = len(queue_manager.failed_downloads)
        
        queue_manager.completed_downloads.clear()
        queue_manager.failed_downloads.clear()
        
        return {
            "message": "Queue cleared successfully",
            "cleared_completed": cleared_completed,
            "cleared_failed": cleared_failed
        }
        
    except Exception as e:
        logger.error(f"Error clearing queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pause")
async def pause_queue():
    """Pause queue processing"""
    try:
        # This would require additional implementation in queue_manager
        return {
            "message": "Queue pause functionality requires additional implementation",
            "status": "not_implemented"
        }
        
    except Exception as e:
        logger.error(f"Error pausing queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/resume")
async def resume_queue():
    """Resume queue processing"""
    try:
        # This would require additional implementation in queue_manager
        return {
            "message": "Queue resume functionality requires additional implementation",
            "status": "not_implemented"
        }
        
    except Exception as e:
        logger.error(f"Error resuming queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_queue_stats():
    """Get detailed queue statistics"""
    try:
        status = queue_manager.get_queue_status()
        
        # Calculate additional stats
        total_processed = status['completed_items'] + status['failed_items']
        success_rate = (status['completed_items'] / total_processed * 100) if total_processed > 0 else 0
        
        return {
            **status,
            "total_processed": total_processed,
            "success_rate": round(success_rate, 2),
            "queue_utilization": len(queue_manager.active_downloads) / queue_manager.max_concurrent * 100
        }
        
    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))