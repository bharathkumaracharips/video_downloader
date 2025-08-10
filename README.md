# Advanced YouTube Downloader

A modern, multi-mode YouTube downloader built with FastAPI and Next.js, powered by yt-dlp. This application provides a clean, professional interface for downloading videos, audio, playlists, and live streams with advanced queue management.

## 🚀 Features

### Download Modes
- **Video Download**: High-quality video downloads with format selection
- **Audio Extraction**: Extract audio in MP3, FLAC, AAC, Opus, WAV formats
- **Playlist Download**: Batch download entire playlists or selected videos
- **Live Stream Recording**: Record live streams and premieres

### Advanced Features
- **Queue Management**: Concurrent downloads with priority handling
- **Progress Tracking**: Real-time download progress and status
- **Format Analysis**: Detailed format information and recommendations
- **Quality Presets**: Easy quality selection (1080p, 720p, etc.)
- **Error Handling**: Robust error handling and retry mechanisms
- **Database Logging**: SQLite database for download history

## 🏗️ Architecture

### Backend (FastAPI)
```
backend/
├── main.py                 # FastAPI application entry point
├── core/
│   ├── config.py          # Configuration settings
│   ├── models.py          # Pydantic models
│   ├── downloader.py      # yt-dlp wrapper
│   ├── database.py        # SQLAlchemy models
│   └── logger.py          # Logging configuration
├── api/routes/
│   ├── video.py           # Video download endpoints
│   ├── audio.py           # Audio extraction endpoints
│   ├── playlist.py        # Playlist download endpoints
│   ├── live.py            # Live stream endpoints
│   ├── formats.py         # Format analysis endpoints
│   └── queue.py           # Queue management endpoints
└── services/
    └── queue_manager.py   # Download queue service
```

### Frontend (Next.js)
- Modern React with TypeScript
- Tailwind CSS for styling
- Real-time progress updates
- Responsive design
- Queue status monitoring

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- Node.js 18+
- FFmpeg (for audio conversion)

### Backend Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd youtube-downloader
```

2. **Set up Python environment**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your settings
```

5. **Run the backend**
```bash
python main.py
```

The API will be available at `http://127.0.0.1:8000`

### Frontend Setup

1. **Install Node.js dependencies**
```bash
npm install
```

2. **Run the development server**
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## 📖 API Documentation

Once the backend is running, visit `http://127.0.0.1:8000/docs` for interactive API documentation.

### Key Endpoints

#### Video Downloads
- `POST /api/video/info` - Get video information
- `POST /api/video/download` - Download video
- `GET /api/video/formats/{video_id}` - Get available formats

#### Audio Downloads
- `POST /api/audio/download` - Download audio
- `POST /api/audio/extract` - Extract audio info
- `GET /api/audio/quality-presets` - Get quality options

#### Playlist Downloads
- `POST /api/playlist/info` - Get playlist information
- `POST /api/playlist/download` - Download playlist
- `GET /api/playlist/download/stream` - Stream download progress

#### Queue Management
- `GET /api/queue/status` - Get queue status
- `GET /api/queue/downloads` - Get all downloads
- `DELETE /api/queue/download/{id}` - Cancel download

## 🎯 Usage Examples

### Download a Video
```bash
curl -X POST "http://127.0.0.1:8000/api/video/download" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "quality": "best[height<=1080]"
  }'
```

### Extract Audio
```bash
curl -X POST "http://127.0.0.1:8000/api/audio/download" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "mp3",
    "quality": "320"
  }'
```

### Download Playlist
```bash
curl -X POST "http://127.0.0.1:8000/api/playlist/download" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/playlist?list=PLrAXtmRdnEQy6nuLMHjMZOz59Oq3KuQEl",
    "mode": "audio",
    "audio_format": "mp3"
  }'
```

## ⚙️ Configuration

### Environment Variables
```env
# Server Configuration
HOST=127.0.0.1
PORT=8000
DEBUG=true

# Download Settings
DOWNLOAD_DIR=downloads
MAX_CONCURRENT_DOWNLOADS=3
MAX_QUEUE_SIZE=100

# yt-dlp Settings
YTDLP_CACHE_DIR=.ytdlp_cache
YTDLP_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Database
DATABASE_URL=sqlite:///./downloads.db
```

## 🔧 Development

### Adding New Features

1. **Backend**: Add new routes in `backend/api/routes/`
2. **Frontend**: Update components in `src/app/`
3. **Models**: Define new Pydantic models in `backend/core/models.py`

### Testing
```bash
# Backend tests
cd backend
python -m pytest

# Frontend tests
npm test
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 🐛 Troubleshooting

### Common Issues

1. **FFmpeg not found**: Install FFmpeg and ensure it's in your PATH
2. **Permission errors**: Check file permissions in the download directory
3. **Network errors**: Verify internet connection and YouTube accessibility

### Logs
Check logs in the `logs/` directory for detailed error information.

## 🙏 Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - The powerful YouTube downloader
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Next.js](https://nextjs.org/) - React framework for production
