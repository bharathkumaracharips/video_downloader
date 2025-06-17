from fastapi import APIRouter
from pydantic import BaseModel
import yt_dlp
import re
from typing import Optional
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
from contextlib import asynccontextmanager

router = APIRouter()

class DownloadState:
    def __init__(self):
        self.is_downloading = False

download_state = DownloadState()

def to_playlist_url(url: str) -> str:
    print(f"[DEBUG] Original URL: {url}")
    # If already a playlist URL, return as is
    if "/playlist?list=" in url:
        print(f"[DEBUG] Already a playlist URL: {url}")
        return url
    match = re.search(r"[?&]list=([a-zA-Z0-9_-]+)", url)
    print(f"[DEBUG] Regex match: {match.group(1) if match else None}")
    if match:
        playlist_url = f"https://www.youtube.com/playlist?list={match.group(1)}"
        print(f"[DEBUG] Converted to playlist URL: {playlist_url}")
        return playlist_url
    print(f"[DEBUG] No list parameter found, returning original URL.")
    return url

class PlaylistRequest(BaseModel):
    url: str

class DownloadPlaylistRequest(BaseModel):
    url: str
    video_ids: list[str]

class StopDownloadRequest(BaseModel):
    pass

@router.post("/stop_download")
async def stop_download(req: StopDownloadRequest):
    download_state.is_downloading = False
    return {"status": "success", "message": "Download stop requested"}

@router.get("/download_playlist_audio")
async def download_playlist_audio(url: str):
    download_state.is_downloading = True

    async def event_generator():
        try:
            playlist_url = to_playlist_url(url)
            downloaded = []
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }],
                'outtmpl': '%(title)s.%(ext)s',
                'ignoreerrors': True,
                'download_archive': 'downloaded.txt',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # First get the playlist info
                playlist_info = ydl.extract_info(playlist_url, download=False)
                total_videos = len(playlist_info['entries'])
                current_video = 0
                
                # Send initial total count
                yield {
                    "event": "total",
                    "data": json.dumps({"total": total_videos})
                }
                
                # Then download each video if we haven't been stopped
                for entry in playlist_info['entries']:
                    if not download_state.is_downloading:
                        yield {
                            "event": "stopped",
                            "data": json.dumps({"message": "Download stopped by user"})
                        }
                        break
                    
                    current_video += 1
                    try:
                        video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                        info = ydl.extract_info(video_url, download=True)
                        filename = ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')
                        
                        # Send progress update
                        yield {
                            "event": "progress",
                            "data": json.dumps({
                                "current": current_video,
                                "total": total_videos,
                                "filename": filename,
                                "status": "success"
                            })
                        }
                        
                        downloaded.append(filename)
                        # Small delay to prevent overwhelming the client
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        error_msg = f"Failed: {entry['id']} ({str(e)})"
                        yield {
                            "event": "progress",
                            "data": json.dumps({
                                "current": current_video,
                                "total": total_videos,
                                "filename": error_msg,
                                "status": "error"
                            })
                        }
                        downloaded.append(error_msg)
                
                # Send completion event
                yield {
                    "event": "complete",
                    "data": json.dumps({
                        "message": "Download complete",
                        "total_downloaded": current_video
                    })
                }
                
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({
                    "message": str(e)
                })
            }
        
        finally:
            download_state.is_downloading = False
    
    return EventSourceResponse(event_generator())

@router.post("/list_playlist")
async def list_playlist(req: PlaylistRequest):
    playlist_url = to_playlist_url(req.url)
    print(f"[DEBUG] Final playlist URL passed to yt-dlp: {playlist_url}")
    ydl_opts = {"extract_flat": True, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
        videos = []
        for idx, entry in enumerate(info.get("entries", []), 1):
            videos.append({
                "id": entry["id"],
                "title": entry.get("title", f"Video {idx}"),
                "index": idx
            })
        return {"videos": videos, "title": info.get("title", playlist_url)}

@router.post("/download_playlist")
async def download_playlist(req: DownloadPlaylistRequest):
    playlist_url = to_playlist_url(req.url)
    print(f"[DEBUG] Final playlist URL passed to yt-dlp: {playlist_url}")
    downloaded = []
    for vid in req.video_ids:
        video_url = f"https://www.youtube.com/watch?v={vid}"
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': f'%(playlist_index)s-%(title)s.%(ext)s',
            'ignoreerrors': True,
            'download_archive': 'downloaded.txt',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(video_url, download=True)
                filename = ydl.prepare_filename(info)
                downloaded.append(filename)
            except Exception as e:
                downloaded.append(f"Failed: {vid} ({str(e)})")
    return {"status": "success", "downloaded": downloaded} 