"""
Database query functions that maintain backward compatibility with file-based data structures.

These functions return the exact same data formats as the current JSON-based system
to ensure zero breaking changes when transitioning to database storage.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from app.database import get_database_session, Video, TranscriptChunk, Speaker
# Utility functions (moved here to avoid circular imports)
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


def get_all_videos_from_database() -> List[Dict[str, Any]]:
    """
    Get all processed videos from database with exact same structure as file-based version.
    
    Returns the same format as processor.get_all_videos() for backward compatibility.
    """
    try:
        session = get_database_session()
        
        # Query videos with aggregate data for word count and speaker count
        videos_query = session.query(
            Video,
            func.coalesce(func.count(TranscriptChunk.id), 0).label('word_count'),
            func.coalesce(func.count(func.distinct(TranscriptChunk.speaker_id)), 0).label('speaker_count')
        ).outerjoin(TranscriptChunk, Video.id == TranscriptChunk.video_id)\
         .group_by(Video.id)\
         .order_by(desc(Video.processed_date))
        
        results = videos_query.all()
        session.close()
        
        videos = []
        for video, word_count, speaker_count in results:
            # Convert database record to exact same format as JSON files
            video_data = {
                'task_id': video.id,  # task_id is the primary key in our system
                'title': video.title,
                'duration': video.duration,
                'uploader': video.uploader,
                'view_count': 0,  # Not stored in database yet, default to 0
                'upload_date': 'Unknown',  # Not stored in database yet  
                'url': video.url,
                'video_id': video.video_id,
                'audio_file': f"/app/data/videos/{video.id}/audio.webm",  # Maintain file path structure
                'processed_date': video.processed_date.isoformat(),
                
                # Computed fields (exactly as in original)
                'word_count': word_count or 0,
                'speaker_count': speaker_count or 0,
                'duration_formatted': format_duration(video.duration),
                'processed_date_formatted': format_date(video.processed_date.isoformat())
            }
            videos.append(video_data)
        
        return videos
        
    except Exception as e:
        logger.error(f"Database error in get_all_videos_from_database: {str(e)}")
        # Return empty list on error - let fallback mechanism handle it
        return []


def get_task_result_from_database(task_id: str) -> Dict[str, Any]:
    """
    Get video result from database with exact same structure as file-based version.
    
    Returns the same format as processor.get_task_result() for backward compatibility.
    """
    try:
        session = get_database_session()
        
        # Get video metadata
        video = session.query(Video).filter(Video.id == task_id).first()
        if not video:
            session.close()
            return {}
        
        # Get transcript chunks in order
        transcript_chunks = session.query(TranscriptChunk)\
            .filter(TranscriptChunk.video_id == task_id)\
            .order_by(TranscriptChunk.start_ms)\
            .all()
        
        session.close()
        
        # Build metadata in exact same format as JSON file version
        metadata = {
            'task_id': video.id,
            'title': video.title,
            'duration': video.duration,
            'uploader': video.uploader,
            'view_count': 0,  # Not stored in database yet
            'upload_date': 'Unknown',  # Not stored in database yet
            'url': video.url,
            'video_id': video.video_id,
            'audio_file': f"/app/data/videos/{video.id}/audio.webm",  # Maintain expected path
            'processed_date': video.processed_date.isoformat(),
            
            # Add formatted fields exactly as original
            'duration_formatted': format_duration(video.duration),
            'processed_date_formatted': format_date(video.processed_date.isoformat())
        }
        
        # Build transcript in exact same format as ElevenLabs API response
        transcript = {
            'language_code': 'eng',  # Default - not stored separately yet
            'language_probability': 1.0,  # Default - not stored separately yet
            'text': ' '.join([chunk.text for chunk in transcript_chunks]),
            'words': []
        }
        
        # Convert database chunks back to ElevenLabs word format
        for chunk in transcript_chunks:
            # Split chunk text into individual words for backward compatibility
            # This maintains the expected transcript structure
            words = chunk.text.split()
            words_per_ms = (chunk.end_ms - chunk.start_ms) / max(len(words), 1)
            
            for i, word in enumerate(words):
                word_start = chunk.start_ms + int(i * words_per_ms)
                word_end = chunk.start_ms + int((i + 1) * words_per_ms)
                
                transcript['words'].append({
                    'start_ms': word_start,
                    'end_ms': word_end,
                    'text': word,
                    'speaker_id': chunk.speaker_id or 'speaker_0',  # Default speaker if none
                    'speaker': chunk.speaker_id or 'speaker_0'  # Compatibility field
                })
        
        return {
            'metadata': metadata,
            'transcript': transcript
        }
        
    except Exception as e:
        logger.error(f"Database error in get_task_result_from_database: {str(e)}")
        # Return empty dict on error - let fallback mechanism handle it
        return {}


def save_video_to_database(metadata: Dict[str, Any], transcript: Dict[str, Any]) -> bool:
    """
    Save video metadata and transcript to database.
    
    This function is called alongside JSON file creation to maintain dual storage.
    Returns True if successful, False otherwise.
    """
    try:
        session = get_database_session()
        
        # Create video record
        video = Video(
            id=metadata['task_id'],
            title=metadata['title'],
            duration=metadata['duration'],
            uploader=metadata['uploader'],
            url=metadata['url'],
            video_id=metadata['video_id'],
            processed_date=datetime.fromisoformat(metadata['processed_date'])
        )
        
        session.add(video)
        
        # Create transcript chunks
        transcript_chunks = []
        speakers_seen = set()
        
        # Process transcript words into chunks
        if 'words' in transcript and isinstance(transcript['words'], list):
            # Group words into chunks (e.g., by speaker or time segments)
            current_speaker = None
            current_chunk_words = []
            current_start_ms = None
            
            for word in transcript['words']:
                word_speaker = word.get('speaker_id') or word.get('speaker') or 'speaker_0'
                word_start = word.get('start_ms', 0)
                word_end = word.get('end_ms', 0)
                word_text = word.get('text', '')
                
                speakers_seen.add(word_speaker)
                
                # Start new chunk if speaker changes or chunk gets too long
                if (current_speaker != word_speaker or 
                    len(current_chunk_words) >= 50 or  # Max words per chunk
                    current_start_ms is None):
                    
                    # Save previous chunk if exists
                    if current_chunk_words and current_start_ms is not None:
                        chunk_text = ' '.join(current_chunk_words)
                        chunk = TranscriptChunk(
                            video_id=metadata['task_id'],
                            start_ms=current_start_ms,
                            end_ms=prev_word_end,
                            speaker_id=current_speaker,
                            text=chunk_text,
                            word_count=len(current_chunk_words)
                        )
                        transcript_chunks.append(chunk)
                    
                    # Start new chunk
                    current_speaker = word_speaker
                    current_chunk_words = [word_text]
                    current_start_ms = word_start
                else:
                    # Add to current chunk
                    current_chunk_words.append(word_text)
                
                prev_word_end = word_end
            
            # Save final chunk
            if current_chunk_words and current_start_ms is not None:
                chunk_text = ' '.join(current_chunk_words)
                chunk = TranscriptChunk(
                    video_id=metadata['task_id'],
                    start_ms=current_start_ms,
                    end_ms=prev_word_end,
                    speaker_id=current_speaker,
                    text=chunk_text,
                    word_count=len(current_chunk_words)
                )
                transcript_chunks.append(chunk)
        
        # Add all chunks
        session.add_all(transcript_chunks)
        
        # Create speaker records
        for speaker_id in speakers_seen:
            speaker = Speaker(
                video_id=metadata['task_id'],
                speaker_id=speaker_id,
                name=None  # Name not available from transcript
            )
            session.add(speaker)
        
        # Commit all changes
        session.commit()
        session.close()
        
        logger.info(f"Successfully saved video {metadata['task_id']} to database")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save video to database: {str(e)}")
        session.rollback()
        session.close()
        return False


def check_video_exists_in_database(task_id: str) -> bool:
    """Check if a video exists in the database."""
    try:
        session = get_database_session()
        exists = session.query(Video).filter(Video.id == task_id).first() is not None
        session.close()
        return exists
    except Exception:
        return False


def get_database_stats() -> Dict[str, Any]:
    """Get database statistics for monitoring."""
    try:
        session = get_database_session()
        
        video_count = session.query(Video).count()
        chunk_count = session.query(TranscriptChunk).count()
        speaker_count = session.query(Speaker).count()
        
        # Get latest video
        latest_video = session.query(Video)\
            .order_by(desc(Video.processed_date))\
            .first()
        
        session.close()
        
        return {
            'video_count': video_count,
            'chunk_count': chunk_count,
            'speaker_count': speaker_count,
            'latest_video_date': latest_video.processed_date.isoformat() if latest_video else None,
            'database_healthy': True
        }
        
    except Exception as e:
        logger.error(f"Database stats error: {str(e)}")
        return {
            'video_count': 0,
            'chunk_count': 0,
            'speaker_count': 0,
            'latest_video_date': None,
            'database_healthy': False,
            'error': str(e)
        }