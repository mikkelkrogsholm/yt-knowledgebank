import yt_dlp
import os
import asyncio
from typing import Dict, Any

# Simple in-memory progress store
progress_store: Dict[str, Dict] = {}

async def process_youtube_url(url: str, task_id: str) -> Dict[str, Any]:
    """
    Process a YouTube URL and download the audio as MP3
    Returns metadata about the processed video
    """
    
    # Create data directory if it doesn't exist
    data_dir = "/app/data"
    os.makedirs(data_dir, exist_ok=True)
    
    # Initialize progress tracking
    progress_store[task_id] = {"status": "starting", "percent": 0}
    
    # Progress hook for yt-dlp
    def progress_hook(d):
        if d['status'] == 'downloading':
            try:
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if total > 0:
                    percent = (downloaded / total) * 100
                else:
                    percent = 0
                
                progress_store[task_id] = {
                    "status": "downloading",
                    "percent": round(percent, 1),
                    "speed": d.get('speed', 0),
                    "eta": d.get('eta', 0)
                }
            except (TypeError, ZeroDivisionError):
                progress_store[task_id] = {"status": "downloading", "percent": 0}
        elif d['status'] == 'finished':
            progress_store[task_id] = {"status": "processing", "percent": 90}
    
    # Configure yt-dlp options
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{data_dir}/%(title)s.%(ext)s',
        'progress_hooks': [progress_hook],
        'noplaylist': True,
    }
    
    # Run yt-dlp in a thread to avoid blocking
    def download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First, extract info without downloading
            info = ydl.extract_info(url, download=False)
            
            # Then download
            ydl.download([url])
            
            # Update progress to finished
            progress_store[task_id] = {"status": "finished", "percent": 100}
            
            # Get the actual file extension from the format
            ext = info.get('ext', 'webm')
            
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown'),
                'view_count': info.get('view_count', 0),
                'upload_date': info.get('upload_date', 'Unknown'),
                'filename': f"{info.get('title', 'Unknown')}.{ext}"
            }
    
    # Run the download in a thread to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, download)
    
    return result