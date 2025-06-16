from fastapi import APIRouter
from pydantic import BaseModel
import yt_dlp
import re

router = APIRouter()

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