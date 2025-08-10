"""
Database models and operations
"""

from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from datetime import datetime
import json

from core.config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DownloadRecord(Base):
    __tablename__ = "downloads"
    
    id = Column(String, primary_key=True, index=True)
    url = Column(String, nullable=False)
    title = Column(String)
    mode = Column(String, nullable=False)  # video, audio, playlist, etc.
    status = Column(String, nullable=False, default="pending")
    progress = Column(Float, default=0.0)
    filename = Column(String)
    file_path = Column(String)
    file_size = Column(Integer)
    error_message = Column(Text)
    options = Column(Text)  # JSON string of download options
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime)

class QueueItem(Base):
    __tablename__ = "queue"
    
    id = Column(String, primary_key=True, index=True)
    download_id = Column(String, nullable=False)
    priority = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime)

async def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()