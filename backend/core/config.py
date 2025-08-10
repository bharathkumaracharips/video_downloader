"""
Configuration settings for the application
"""

from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Server settings
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Download settings
    DOWNLOAD_DIR: str = "downloads"
    MAX_CONCURRENT_DOWNLOADS: int = 3
    MAX_QUEUE_SIZE: int = 100
    
    # yt-dlp settings
    YTDLP_CACHE_DIR: str = ".ytdlp_cache"
    YTDLP_COOKIES_FILE: str = None
    YTDLP_USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    # Database settings
    DATABASE_URL: str = "sqlite:///./downloads.db"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create downloads directory
def ensure_directories():
    dirs = [
        settings.DOWNLOAD_DIR,
        settings.YTDLP_CACHE_DIR,
        "logs"
    ]
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)

settings = Settings()
ensure_directories()