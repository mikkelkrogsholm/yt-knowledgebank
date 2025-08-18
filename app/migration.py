"""
Migration system for YouTube Knowledgebank - Phase 1 Task 2
Migrates existing JSON data from /data/videos/ to SQLite database.
"""
import json
import logging
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

from app.database import DatabaseManager, Video, TranscriptChunk, Speaker
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def discover_video_data(videos_directory: str) -> List[Dict[str, Any]]:
    """
    Discover and load video data from JSON files in videos directory.
    
    Args:
        videos_directory: Path to the videos directory containing subdirectories with JSON files
        
    Returns:
        List of dictionaries containing video data with keys:
        - task_id: Video task ID (UUID)
        - metadata: Parsed metadata.json content
        - transcript: Parsed transcript.json content
    """
    videos_path = Path(videos_directory)
    discovered_videos = []
    
    if not videos_path.exists():
        logger.warning(f"Videos directory does not exist: {videos_directory}")
        return discovered_videos
    
    # Iterate through all subdirectories
    for video_dir in videos_path.iterdir():
        if not video_dir.is_dir():
            continue
        
        task_id = video_dir.name
        metadata_path = video_dir / "metadata.json"
        transcript_path = video_dir / "transcript.json"
        
        # Both files must exist for valid video data
        if not (metadata_path.exists() and transcript_path.exists()):
            logger.warning(f"Skipping {task_id}: missing metadata.json or transcript.json")
            continue
        
        try:
            # Load metadata
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Load transcript  
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript = json.load(f)
            
            # Add to discovered videos
            discovered_videos.append({
                "task_id": task_id,
                "metadata": metadata,
                "transcript": transcript
            })
            
            logger.debug(f"Discovered video: {task_id}")
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {task_id}: {e}")
            continue
        except Exception as e:
            logger.error(f"Error loading data for {task_id}: {e}")
            continue
    
    logger.info(f"Discovered {len(discovered_videos)} videos for migration")
    return discovered_videos


def validate_json_structure(data: Dict[str, Any], data_type: str) -> bool:
    """
    Validate JSON structure for metadata or transcript data.
    
    Args:
        data: JSON data to validate
        data_type: Type of data ("metadata" or "transcript")
        
    Returns:
        True if data structure is valid, False otherwise
    """
    if data_type == "metadata":
        required_fields = [
            "task_id", "title", "duration", "uploader", 
            "url", "video_id", "processed_date"
        ]
        
        for field in required_fields:
            if field not in data:
                logger.warning(f"Missing required metadata field: {field}")
                return False
        
        # Validate data types
        if not isinstance(data.get("duration"), int):
            logger.warning("Duration must be an integer")
            return False
        
        return True
    
    elif data_type == "transcript":
        required_fields = ["text", "words"]
        
        for field in required_fields:
            if field not in data:
                logger.warning(f"Missing required transcript field: {field}")
                return False
        
        # Validate words array
        if not isinstance(data.get("words"), list):
            logger.warning("Words must be a list")
            return False
        
        return True
    
    else:
        logger.error(f"Unknown data type for validation: {data_type}")
        return False


def transform_metadata(json_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform JSON metadata to Video model format.
    
    Args:
        json_metadata: Raw metadata from JSON file
        
    Returns:
        Dictionary with Video model fields
    """
    # Parse the processed_date string to datetime
    processed_date_str = json_metadata["processed_date"]
    processed_date = datetime.fromisoformat(processed_date_str)
    
    # Map JSON fields to Video model fields
    video_data = {
        "id": json_metadata["task_id"],
        "title": json_metadata["title"],
        "duration": json_metadata["duration"],
        "uploader": json_metadata["uploader"],
        "url": json_metadata["url"],
        "video_id": json_metadata["video_id"],
        "processed_date": processed_date
    }
    
    return video_data


def extract_speakers(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract unique speakers from transcript words.
    
    Args:
        words: List of word dictionaries from transcript
        
    Returns:
        List of speaker dictionaries with speaker_id and name (null)
    """
    unique_speakers = set()
    
    for word in words:
        speaker_id = word.get("speaker_id")
        if speaker_id is not None:
            unique_speakers.add(speaker_id)
    
    speakers = []
    for speaker_id in sorted(unique_speakers):
        speakers.append({
            "speaker_id": speaker_id,
            "name": None  # No name information in current data
        })
    
    return speakers


def process_transcript(transcript: Dict[str, Any], chunk_size_words: int = 50) -> List[Dict[str, Any]]:
    """
    Process transcript into chunks for database storage.
    
    Args:
        transcript: Raw transcript from JSON file
        chunk_size_words: Maximum words per chunk
        
    Returns:
        List of transcript chunk dictionaries
    """
    words = transcript.get("words", [])
    full_text = transcript.get("text", "")
    
    # Handle empty words array
    if not words:
        if full_text:
            # Create a single chunk with the full text
            return [{
                "start_ms": 0,
                "end_ms": 0,
                "speaker_id": None,
                "text": full_text,
                "word_count": len(full_text.split())
            }]
        else:
            return []
    
    chunks = []
    current_chunk_words = []
    current_speaker = None
    
    def finalize_chunk():
        """Finalize current chunk and add to chunks list."""
        if not current_chunk_words:
            return
        
        # Calculate timestamps (convert seconds to milliseconds)
        start_ms = int(current_chunk_words[0].get("start", 0) * 1000)
        end_ms = int(current_chunk_words[-1].get("end", 0) * 1000)
        
        # Build text from words, preserving spacing
        chunk_text = ""
        for i, word_data in enumerate(current_chunk_words):
            text = word_data.get("text", "")
            if word_data.get("type") == "spacing":
                chunk_text += text
            else:
                # Add space before word if it's not the first word
                if i > 0 and chunk_text and not chunk_text.endswith(" "):
                    chunk_text += " "
                chunk_text += text
        
        chunk = {
            "start_ms": start_ms,
            "end_ms": end_ms,
            "speaker_id": current_speaker,
            "text": chunk_text.strip(),
            "word_count": len([w for w in current_chunk_words if w.get("type") != "spacing"])
        }
        
        chunks.append(chunk)
    
    # Process words into chunks
    for word_data in words:
        word_speaker = word_data.get("speaker_id")
        
        # Start new chunk if speaker changes or chunk is full
        if (current_speaker is not None and word_speaker != current_speaker) or \
           len([w for w in current_chunk_words if w.get("type") != "spacing"]) >= chunk_size_words:
            finalize_chunk()
            current_chunk_words = []
        
        current_chunk_words.append(word_data)
        current_speaker = word_speaker
    
    # Finalize the last chunk
    finalize_chunk()
    
    return chunks


class MigrationManager:
    """
    Manages the migration of video data from JSON files to SQLite database.
    """
    
    def __init__(
        self, 
        videos_directory: str, 
        database_manager: DatabaseManager,
        batch_size: int = 100,
        chunk_size_words: int = 50
    ):
        """
        Initialize migration manager.
        
        Args:
            videos_directory: Path to videos directory
            database_manager: Database manager instance
            batch_size: Number of videos to process in each batch
            chunk_size_words: Maximum words per transcript chunk
        """
        self.videos_directory = videos_directory
        self.database_manager = database_manager
        self.batch_size = batch_size
        self.chunk_size_words = chunk_size_words
    
    def run_migration(self) -> Dict[str, Any]:
        """
        Run the complete migration process.
        
        Returns:
            Migration result dictionary with status, statistics, and any errors
        """
        start_time = time.time()
        result = {
            "status": "success",
            "videos_migrated": 0,
            "transcript_chunks_created": 0,
            "speakers_created": 0,
            "errors": [],
            "performance": {}
        }
        
        try:
            # Discover video data
            logger.info(f"Starting migration from {self.videos_directory}")
            video_data_list = discover_video_data(self.videos_directory)
            
            if not video_data_list:
                result["message"] = f"No video data found to migrate in {self.videos_directory}"
                logger.info(result["message"])
                result["performance"]["duration_seconds"] = time.time() - start_time
                return result
            
            # Process videos in batches
            with self.database_manager.get_session() as session:
                for i in range(0, len(video_data_list), self.batch_size):
                    batch = video_data_list[i:i + self.batch_size]
                    batch_result = self._process_batch(session, batch)
                    
                    # Aggregate results
                    result["videos_migrated"] += batch_result["videos_migrated"]
                    result["transcript_chunks_created"] += batch_result["transcript_chunks_created"]
                    result["speakers_created"] += batch_result["speakers_created"]
                    result["errors"].extend(batch_result["errors"])
                    
                    if batch_result["status"] == "error":
                        result["status"] = "error"
                        break
                
                # Commit the transaction
                if result["status"] == "success":
                    session.commit()
                    logger.info("Migration completed successfully")
                else:
                    session.rollback()
                    logger.error("Migration failed, rolled back all changes")
        
        except Exception as e:
            result["status"] = "error"
            result["errors"].append(f"Migration failed with error: {str(e)}")
            logger.error(f"Migration failed: {e}", exc_info=True)
        
        # Performance metrics
        end_time = time.time()
        result["performance"]["duration_seconds"] = end_time - start_time
        result["message"] = f"Migrated {result['videos_migrated']} videos with {len(result['errors'])} errors"
        
        return result
    
    def _process_batch(self, session, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a batch of videos.
        
        Args:
            session: Database session
            batch: List of video data dictionaries
            
        Returns:
            Batch processing result
        """
        batch_result = {
            "status": "success",
            "videos_migrated": 0,
            "transcript_chunks_created": 0,
            "speakers_created": 0,
            "errors": []
        }
        
        try:
            for video_data in batch:
                video_result = self._process_video(session, video_data)
                
                if video_result["status"] == "success":
                    batch_result["videos_migrated"] += 1
                    batch_result["transcript_chunks_created"] += video_result["transcript_chunks_created"]
                    batch_result["speakers_created"] += video_result["speakers_created"]
                else:
                    batch_result["errors"].extend(video_result["errors"])
                    batch_result["status"] = "error"
                    # Continue processing other videos in batch but mark batch as failed
        
        except Exception as e:
            batch_result["status"] = "error"
            batch_result["errors"].append(f"Batch processing failed: {str(e)}")
            logger.error(f"Batch processing failed: {e}", exc_info=True)
        
        return batch_result
    
    def _process_video(self, session, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single video and its associated data.
        
        Args:
            session: Database session
            video_data: Video data dictionary from discover_video_data()
            
        Returns:
            Video processing result
        """
        video_result = {
            "status": "success",
            "transcript_chunks_created": 0,
            "speakers_created": 0,
            "errors": []
        }
        
        task_id = video_data["task_id"]
        
        try:
            # Validate data structure
            if not validate_json_structure(video_data["metadata"], "metadata"):
                video_result["status"] = "error"
                video_result["errors"].append(f"Invalid metadata structure for {task_id}")
                return video_result
            
            if not validate_json_structure(video_data["transcript"], "transcript"):
                video_result["status"] = "error"
                video_result["errors"].append(f"Invalid transcript structure for {task_id}")
                return video_result
            
            # Transform and create Video record
            video_model_data = transform_metadata(video_data["metadata"])
            video = Video(**video_model_data)
            session.add(video)
            
            # Process transcript chunks
            chunks = process_transcript(video_data["transcript"], self.chunk_size_words)
            for chunk_data in chunks:
                chunk = TranscriptChunk(
                    video_id=task_id,
                    start_ms=chunk_data["start_ms"],
                    end_ms=chunk_data["end_ms"],
                    speaker_id=chunk_data["speaker_id"],
                    text=chunk_data["text"],
                    word_count=chunk_data["word_count"]
                )
                session.add(chunk)
                video_result["transcript_chunks_created"] += 1
            
            # Process speakers
            speakers = extract_speakers(video_data["transcript"]["words"])
            for speaker_data in speakers:
                speaker = Speaker(
                    video_id=task_id,
                    speaker_id=speaker_data["speaker_id"],
                    name=speaker_data["name"]
                )
                session.add(speaker)
                video_result["speakers_created"] += 1
            
            logger.debug(f"Processed video {task_id}: {video_result['transcript_chunks_created']} chunks, {video_result['speakers_created']} speakers")
        
        except SQLAlchemyError as e:
            video_result["status"] = "error"
            video_result["errors"].append(f"Database error for {task_id}: {str(e)}")
            logger.error(f"Database error processing {task_id}: {e}")
        
        except Exception as e:
            video_result["status"] = "error"
            video_result["errors"].append(f"Error processing {task_id}: {str(e)}")
            logger.error(f"Error processing video {task_id}: {e}", exc_info=True)
        
        return video_result


def run_migration_cli(videos_dir: str = "/app/data/videos", database_url: str = "sqlite:///app/data/knowledge_bank.db"):
    """
    CLI function to run migration.
    
    Args:
        videos_dir: Path to videos directory
        database_url: Database URL
    """
    print("🚀 Starting YouTube Knowledgebank Migration...")
    
    # Initialize database
    print("📊 Initializing database...")
    try:
        from app.database import init_database
        db_manager = init_database(database_url)
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        return 1
    
    # Run migration
    print("📁 Starting migration from JSON files...")
    try:
        migration_manager = MigrationManager(videos_dir, db_manager)
        result = migration_manager.run_migration()
        
        # Print results
        print("\n📈 Migration Results:")
        print(f"   Status: {result['status']}")
        print(f"   Videos Migrated: {result['videos_migrated']}")
        print(f"   Transcript Chunks: {result['transcript_chunks_created']}")
        print(f"   Speakers: {result['speakers_created']}")
        print(f"   Duration: {result['performance']['duration_seconds']:.2f} seconds")
        
        if result['errors']:
            print(f"\n❌ Errors ({len(result['errors'])}):")
            for error in result['errors']:
                print(f"   - {error}")
        
        if result['status'] == 'success' and result['videos_migrated'] > 0:
            print("\n🎉 Migration completed successfully!")
            return 0
        elif result['status'] == 'success' and result['videos_migrated'] == 0:
            print(f"\n📁 {result.get('message', 'No videos found to migrate')}")
            return 0
        else:
            print(f"\n⚠️  Migration completed with errors")
            return 1
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        logger.error(f"Migration CLI failed: {e}", exc_info=True)
        return 1