import yt_dlp
import os
import json
import asyncio
import re
import logging
from typing import Dict, Any, List
from datetime import datetime

# Database integration imports
try:
    from app.database_queries import (
        get_all_videos_from_database,
        get_task_result_from_database, 
        save_video_to_database,
        check_video_exists_in_database,
        format_duration,
        format_date
    )
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    # Define fallback utility functions if database imports fail
    def format_duration(seconds: int) -> str:
        """Format duration in seconds to MM:SS format."""
        if not seconds:
            return "0:00"
        
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}:{secs:02d}"

    def format_date(date_str: str) -> str:
        """Format ISO date string to readable format."""
        if not date_str:
            return "Unknown"
        
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%b %d, %Y")
        except (ValueError, AttributeError):
            return "Unknown"

logger = logging.getLogger(__name__)

# Progress tracking
progress_store: Dict[str, Dict] = {}

def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats"""
    if not url:
        return None
        
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/v\/([^&\n?#]+)',
        r'youtube\.com\/shorts\/([^&\n?#]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

async def process_and_transcribe(url: str, task_id: str, api_key: str) -> Dict[str, Any]:
    """
    Combined function to download YouTube video and transcribe it using ElevenLabs.
    Progress is tracked with phases: downloading (0-50%), transcribing (50-100%)
    """
    
    # Setup directories
    task_dir = f"/app/data/videos/{task_id}"
    os.makedirs(task_dir, exist_ok=True)
    
    try:
        # Phase 1: Download (0-50%)
        progress_store[task_id] = {"phase": "downloading", "percent": 0, "status": "Starting download..."}
        
        def download_hook(d):
            if d['status'] == 'downloading':
                try:
                    downloaded = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    if total > 0:
                        percent = (downloaded / total) * 50  # 0-50% for download phase
                        progress_store[task_id] = {
                            "phase": "downloading",
                            "percent": round(percent, 1),
                            "status": f"Downloading: {round((downloaded / total) * 100, 1)}%"
                        }
                except (TypeError, ZeroDivisionError):
                    progress_store[task_id] = {
                        "phase": "downloading", 
                        "percent": 10,
                        "status": "Downloading..."
                    }
            elif d['status'] == 'finished':
                progress_store[task_id] = {
                    "phase": "downloading",
                    "percent": 50,
                    "status": "Download complete, preparing transcription..."
                }
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{task_dir}/audio.%(ext)s',
            'progress_hooks': [download_hook],
            'noplaylist': True,
        }
        
        # Download audio
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info
        
        # Run download in thread
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, download)
        
        # Get the actual audio file
        ext = info.get('ext', 'webm')
        audio_file = f'{task_dir}/audio.{ext}'
        
        # Extract video ID for embedding
        video_id = extract_video_id(url)
        
        # Save metadata
        metadata = {
            'task_id': task_id,
            'title': info.get('title', 'Unknown'),
            'duration': info.get('duration', 0),
            'uploader': info.get('uploader', 'Unknown'),
            'view_count': info.get('view_count', 0),
            'upload_date': info.get('upload_date', 'Unknown'),
            'url': url,
            'video_id': video_id,
            'audio_file': audio_file,
            'processed_date': datetime.now().isoformat()
        }
        
        with open(f'{task_dir}/metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Phase 2: Transcribe (50-100%)
        progress_store[task_id] = {
            "phase": "transcribing",
            "percent": 55,
            "status": "Starting transcription..."
        }
        
        # Import ElevenLabs here to avoid import error if not installed
        from elevenlabs import ElevenLabs
        
        client = ElevenLabs(api_key=api_key)
        
        progress_store[task_id] = {
            "phase": "transcribing",
            "percent": 70,
            "status": "Uploading audio for transcription..."
        }
        
        # Transcribe audio
        def transcribe():
            with open(audio_file, 'rb') as f:
                transcription = client.speech_to_text.convert(
                    file=f,
                    model_id="scribe_v1",
                    timestamps_granularity="word",
                    diarize=True,
                    tag_audio_events=True
                )
                return transcription
        
        # Run transcription in thread
        transcription = await loop.run_in_executor(None, transcribe)
        
        progress_store[task_id] = {
            "phase": "transcribing",
            "percent": 90,
            "status": "Processing transcription results..."
        }
        
        # Convert transcription to dict if needed
        if hasattr(transcription, 'dict'):
            transcript_data = transcription.dict()
        elif hasattr(transcription, '__dict__'):
            transcript_data = transcription.__dict__
        else:
            transcript_data = transcription
        
        # Save transcript to JSON file
        with open(f'{task_dir}/transcript.json', 'w') as f:
            json.dump(transcript_data, f, indent=2)
        
        # Also save to database if available (dual storage for backward compatibility)
        if DATABASE_AVAILABLE:
            try:
                save_success = save_video_to_database(metadata, transcript_data)
                if save_success:
                    logger.info(f"Successfully saved video {task_id} to database")
                else:
                    logger.warning(f"Failed to save video {task_id} to database")
            except Exception as e:
                logger.error(f"Error saving video {task_id} to database: {str(e)}")
        
        # Mark as completed
        progress_store[task_id] = {
            "phase": "completed",
            "percent": 100,
            "status": "Processing complete!",
            "metadata": metadata,
            "transcript": transcript_data
        }
        
        return {
            "metadata": metadata,
            "transcript": transcript_data
        }
        
    except Exception as e:
        progress_store[task_id] = {
            "phase": "error",
            "percent": 0,
            "status": f"Error: {str(e)}",
            "error": str(e)
        }
        raise e

def get_task_result(task_id: str) -> Dict[str, Any]:
    """
    Get the final result for a completed task.
    
    Uses database if available, falls back to JSON files for backward compatibility.
    """
    # Try database first if available
    if DATABASE_AVAILABLE:
        try:
            database_result = get_task_result_from_database(task_id)
            if database_result:  # If we got results from database
                logger.info(f"Retrieved task {task_id} from database")
                return database_result
        except Exception as e:
            logger.warning(f"Database query failed for task {task_id}, falling back to files: {str(e)}")
    
    # Fallback to original file-based approach
    logger.info(f"Using file-based retrieval for task {task_id}")
    return get_task_result_from_files(task_id)


def get_task_result_from_files(task_id: str) -> Dict[str, Any]:
    """Get the final result for a completed task from JSON files (original implementation)."""
    task_dir = f"/app/data/videos/{task_id}"
    
    result = {}
    
    # Load metadata if available
    metadata_file = f"{task_dir}/metadata.json"
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
            
        # Add formatted fields
        metadata['duration_formatted'] = format_duration(metadata.get('duration', 0))
        metadata['processed_date_formatted'] = format_date(metadata.get('processed_date', ''))
        
        result['metadata'] = metadata
    
    # Load transcript if available
    transcript_file = f"{task_dir}/transcript.json"
    if os.path.exists(transcript_file):
        with open(transcript_file, 'r') as f:
            result['transcript'] = json.load(f)
    
    return result

def get_all_videos() -> List[Dict[str, Any]]:
    """
    Get all processed videos with metadata and stats.
    
    Uses database if available, falls back to JSON files for backward compatibility.
    """
    # Try database first if available
    if DATABASE_AVAILABLE:
        try:
            database_videos = get_all_videos_from_database()
            if database_videos:  # If we got results from database
                logger.info(f"Retrieved {len(database_videos)} videos from database")
                return database_videos
        except Exception as e:
            logger.warning(f"Database query failed, falling back to file system: {str(e)}")
    
    # Fallback to original file-based approach
    logger.info("Using file-based video retrieval")
    return get_all_videos_from_files()


def get_all_videos_from_files() -> List[Dict[str, Any]]:
    """Get all processed videos from JSON files (original implementation)."""
    videos = []
    videos_dir = "/app/data/videos"
    
    if not os.path.exists(videos_dir):
        return videos
    
    for task_id in os.listdir(videos_dir):
        task_dir = f"{videos_dir}/{task_id}"
        
        if not os.path.isdir(task_dir):
            continue
            
        metadata_file = f"{task_dir}/metadata.json"
        transcript_file = f"{task_dir}/transcript.json"
        
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                # Add task_id to metadata
                metadata['task_id'] = task_id
                
                # Add word count from transcript if available
                word_count = 0
                speaker_count = 0
                if os.path.exists(transcript_file):
                    try:
                        with open(transcript_file, 'r') as f:
                            transcript = json.load(f)
                            
                        # Count words
                        if 'words' in transcript and isinstance(transcript['words'], list):
                            word_count = len(transcript['words'])
                            
                            # Count unique speakers
                            speakers = set()
                            for word in transcript['words']:
                                speaker = word.get('speaker_id') or word.get('speaker')
                                if speaker:
                                    speakers.add(speaker)
                            speaker_count = len(speakers)
                        elif 'text' in transcript:
                            word_count = len(transcript['text'].split())
                            
                    except (json.JSONDecodeError, KeyError):
                        pass
                
                # Add computed fields
                metadata['word_count'] = word_count
                metadata['speaker_count'] = speaker_count
                metadata['duration_formatted'] = format_duration(metadata.get('duration', 0))
                metadata['processed_date_formatted'] = format_date(metadata.get('processed_date', ''))
                
                videos.append(metadata)
                
            except (json.JSONDecodeError, FileNotFoundError):
                continue
    
    # Sort by processed date (most recent first)
    return sorted(videos, key=lambda x: x.get('processed_date', ''), reverse=True)

