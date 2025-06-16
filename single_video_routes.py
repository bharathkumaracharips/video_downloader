from fastapi import APIRouter
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import yt_dlp
from video_audio_merger import merge_video_audio

router = APIRouter()

class URLRequest(BaseModel):
    url: str

class DownloadRequest(BaseModel):
    url: str
    format_ids: list[str]

class MergeRequest(BaseModel):
    video_path: str
    audio_path: str
    output_path: str

@router.post("/list_formats")
async def list_formats(req: URLRequest):
    ydl_opts = {}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(req.url, download=False)
        formats = info.get('formats', [])
        result = []
        for f in formats:
            vtype = []
            if f.get('vcodec') != 'none':
                vtype.append('video')
            if f.get('acodec') != 'none':
                vtype.append('audio')
            vtype = '+'.join(vtype) if vtype else 'unknown'
            result.append({
                'format_id': f['format_id'],
                'ext': f.get('ext',''),
                'resolution': f.get('resolution','') or f.get('height',''),
                'fps': f.get('fps',''),
                'type': vtype,
                'note': f.get('format_note',''),
            })
        return {"formats": result, "title": info.get('title', req.url)}

@router.post("/download")
async def download(req: DownloadRequest):
    downloaded_files = []
    for fid in req.format_ids:
        ydl_opts = {
            'format': fid,
            'outtmpl': f'%(title)s_{fid}.%(ext)s'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=True)
            filename = ydl.prepare_filename(info)
            downloaded_files.append(filename)
    return {"status": "success", "files": downloaded_files}

@router.post("/merge")
async def merge(req: MergeRequest):
    try:
        merge_video_audio(req.video_path, req.audio_path, req.output_path)
        return {"status": "success", "output": req.output_path}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)}) 