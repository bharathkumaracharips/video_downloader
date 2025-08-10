"""
Pydantic models for request/response schemas
"""

from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
from datetime import datetime

class DownloadMode(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    PLAYLIST_VIDEO = "playlist_video"
    PLAYLIST_AUDIO = "playlist_audio"
    LIVE = "live"

class QualityPreset(str, Enum):
    BEST = "best"
    WORST = "worst"
    AUDIO_ONLY = "bestaudio"
    VIDEO_ONLY = "bestvideo"
    HD = "best[height<=720]"
    FHD = "best[height<=1080]"
    UHD = "best[height<=2160]"

class DownloadStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# Request Models
class URLRequest(BaseModel):
    url: HttpUrl
    
class VideoDownloadRequest(BaseModel):
    url: HttpUrl
    quality: QualityPreset = QualityPreset.BEST
    format_id: Optional[str] = None
    output_template: Optional[str] = None
    subtitle_langs: Optional[List[str]] = None

class AudioDownloadRequest(BaseModel):
    url: HttpUrl
    quality: Literal["best", "320", "256", "192", "128"] = "best"
    format: Literal["mp3", "aac", "flac", "opus", "wav"] = "mp3"
    output_template: Optional[str] = None

class PlaylistDownloadRequest(BaseModel):
    url: HttpUrl
    mode: Literal["video", "audio"] = "video"
    quality: QualityPreset = QualityPreset.BEST
    audio_format: Literal["mp3", "aac", "flac", "opus"] = "mp3"
    audio_quality: Literal["best", "320", "256", "192", "128"] = "best"
    video_ids: Optional[List[str]] = None
    start_index: Optional[int] = None
    end_index: Optional[int] = None

class LiveStreamRequest(BaseModel):
    url: HttpUrl
    quality: QualityPreset = QualityPreset.BEST
    duration: Optional[int] = None  # seconds
    wait_for_live: bool = True

# Response Models
class FormatInfo(BaseModel):
    format_id: str
    ext: str
    resolution: Optional[str] = None
    fps: Optional[float] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    filesize: Optional[int] = None
    filesize_approx: Optional[int] = None
    tbr: Optional[float] = None
    vbr: Optional[float] = None
    abr: Optional[float] = None
    format_note: Optional[str] = None
    quality: Optional[float] = None
    has_video: bool = False
    has_audio: bool = False

class VideoInfo(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    uploader: Optional[str] = None
    upload_date: Optional[str] = None
    duration: Optional[int] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    thumbnail: Optional[str] = None
    formats: List[FormatInfo] = []
    subtitles: Optional[Dict[str, Any]] = None
    is_live: bool = False
    live_status: Optional[str] = None

class PlaylistInfo(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    uploader: Optional[str] = None
    video_count: int
    videos: List[Dict[str, Any]] = []

class DownloadProgress(BaseModel):
    download_id: str
    status: DownloadStatus
    progress: float = 0.0
    speed: Optional[str] = None
    eta: Optional[str] = None
    downloaded_bytes: Optional[int] = None
    total_bytes: Optional[int] = None
    filename: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class DownloadResponse(BaseModel):
    download_id: str
    status: DownloadStatus
    message: str
    filename: Optional[str] = None
    file_path: Optional[str] = None
    download_url: Optional[str] = None

class QueueStatus(BaseModel):
    total_items: int
    pending_items: int
    active_downloads: int
    completed_items: int
    failed_items: int