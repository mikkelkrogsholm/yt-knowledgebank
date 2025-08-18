"""
Test suite for migration system - Phase 1 Task 2
Testing data migration from JSON files to SQLite database.
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, Mock

from app.migration import (
    MigrationManager,
    discover_video_data,
    validate_json_structure,
    transform_metadata,
    process_transcript,
    extract_speakers
)
from app.database import init_database, get_database_session, Video, TranscriptChunk, Speaker


class TestVideoDataDiscovery:
    """Test JSON file discovery in /data/videos/ directory."""
    
    def test_discover_video_data_empty_directory(self):
        """Test discovery with no video directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            videos_dir = Path(temp_dir) / "videos"
            videos_dir.mkdir()
            
            discovered = discover_video_data(str(videos_dir))
            
            assert discovered == []
    
    def test_discover_video_data_single_video(self):
        """Test discovery with one complete video directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            videos_dir = Path(temp_dir) / "videos"
            video_dir = videos_dir / "test-uuid-123"
            video_dir.mkdir(parents=True)
            
            # Create metadata.json
            metadata = {
                "task_id": "test-uuid-123",
                "title": "Test Video",
                "duration": 300,
                "uploader": "Test Channel",
                "url": "https://youtu.be/test123",
                "video_id": "test123",
                "processed_date": "2024-01-01T00:00:00.000000"
            }
            with open(video_dir / "metadata.json", "w") as f:
                json.dump(metadata, f)
            
            # Create transcript.json
            transcript = {
                "text": "Hello world test transcript",
                "language_code": "eng",
                "words": [
                    {"text": "Hello", "start": 0.0, "end": 0.5, "speaker_id": "speaker_0"},
                    {"text": "world", "start": 0.6, "end": 1.0, "speaker_id": "speaker_0"}
                ]
            }
            with open(video_dir / "transcript.json", "w") as f:
                json.dump(transcript, f)
            
            discovered = discover_video_data(str(videos_dir))
            
            assert len(discovered) == 1
            assert discovered[0]["task_id"] == "test-uuid-123"
            assert discovered[0]["metadata"] == metadata
            assert discovered[0]["transcript"] == transcript
    
    def test_discover_video_data_multiple_videos(self):
        """Test discovery with multiple video directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            videos_dir = Path(temp_dir) / "videos"
            
            # Create multiple video directories
            for i, uuid in enumerate(["uuid-1", "uuid-2", "uuid-3"]):
                video_dir = videos_dir / uuid
                video_dir.mkdir(parents=True)
                
                metadata = {
                    "task_id": uuid,
                    "title": f"Test Video {i+1}",
                    "duration": 300 + i * 60,
                    "uploader": f"Channel {i+1}",
                    "url": f"https://youtu.be/test{i+1}",
                    "video_id": f"test{i+1}",
                    "processed_date": "2024-01-01T00:00:00.000000"
                }
                with open(video_dir / "metadata.json", "w") as f:
                    json.dump(metadata, f)
                
                transcript = {
                    "text": f"Transcript {i+1}",
                    "words": [
                        {"text": f"Word{i+1}", "start": 0.0, "end": 1.0, "speaker_id": "speaker_0"}
                    ]
                }
                with open(video_dir / "transcript.json", "w") as f:
                    json.dump(transcript, f)
            
            discovered = discover_video_data(str(videos_dir))
            
            assert len(discovered) == 3
            task_ids = [item["task_id"] for item in discovered]
            assert "uuid-1" in task_ids
            assert "uuid-2" in task_ids  
            assert "uuid-3" in task_ids
    
    def test_discover_video_data_missing_files(self):
        """Test discovery handles missing metadata or transcript files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            videos_dir = Path(temp_dir) / "videos"
            
            # Video with missing transcript
            video1_dir = videos_dir / "uuid-missing-transcript"
            video1_dir.mkdir(parents=True)
            metadata1 = {"task_id": "uuid-missing-transcript", "title": "Test"}
            with open(video1_dir / "metadata.json", "w") as f:
                json.dump(metadata1, f)
            
            # Video with missing metadata  
            video2_dir = videos_dir / "uuid-missing-metadata"
            video2_dir.mkdir(parents=True)
            transcript2 = {"text": "test", "words": []}
            with open(video2_dir / "transcript.json", "w") as f:
                json.dump(transcript2, f)
            
            # Complete video for comparison
            video3_dir = videos_dir / "uuid-complete"
            video3_dir.mkdir(parents=True)
            metadata3 = {"task_id": "uuid-complete", "title": "Complete"}
            transcript3 = {"text": "complete", "words": []}
            with open(video3_dir / "metadata.json", "w") as f:
                json.dump(metadata3, f)
            with open(video3_dir / "transcript.json", "w") as f:
                json.dump(transcript3, f)
            
            discovered = discover_video_data(str(videos_dir))
            
            # Should only discover the complete video
            assert len(discovered) == 1
            assert discovered[0]["task_id"] == "uuid-complete"


class TestJSONValidation:
    """Test JSON structure validation."""
    
    def test_validate_metadata_structure_valid(self):
        """Test validation of valid metadata structure."""
        metadata = {
            "task_id": "test-123",
            "title": "Test Video",
            "duration": 300,
            "uploader": "Test Channel",
            "url": "https://youtu.be/test",
            "video_id": "test",
            "processed_date": "2024-01-01T00:00:00.000000"
        }
        
        result = validate_json_structure(metadata, "metadata")
        assert result is True
    
    def test_validate_metadata_structure_missing_required_fields(self):
        """Test validation fails with missing required fields."""
        metadata = {
            "task_id": "test-123",
            # Missing title, duration, etc.
        }
        
        result = validate_json_structure(metadata, "metadata")
        assert result is False
    
    def test_validate_transcript_structure_valid(self):
        """Test validation of valid transcript structure."""
        transcript = {
            "text": "Hello world",
            "language_code": "eng",
            "words": [
                {"text": "Hello", "start": 0.0, "end": 0.5, "speaker_id": "speaker_0"},
                {"text": "world", "start": 0.6, "end": 1.0, "speaker_id": "speaker_0"}
            ]
        }
        
        result = validate_json_structure(transcript, "transcript")
        assert result is True
    
    def test_validate_transcript_structure_missing_words(self):
        """Test validation fails with missing words array."""
        transcript = {
            "text": "Hello world",
            "language_code": "eng"
            # Missing words array
        }
        
        result = validate_json_structure(transcript, "transcript")
        assert result is False


class TestMetadataTransformation:
    """Test metadata transformation from JSON to Video model."""
    
    def test_transform_metadata_basic(self):
        """Test basic metadata transformation."""
        json_metadata = {
            "task_id": "test-uuid-123",
            "title": "Amazing Video Title",
            "duration": 1800,
            "uploader": "Cool Channel",
            "url": "https://youtu.be/abc123",
            "video_id": "abc123",
            "processed_date": "2024-01-15T10:30:45.123456"
        }
        
        video_data = transform_metadata(json_metadata)
        
        assert video_data["id"] == "test-uuid-123"
        assert video_data["title"] == "Amazing Video Title"
        assert video_data["duration"] == 1800
        assert video_data["uploader"] == "Cool Channel"
        assert video_data["url"] == "https://youtu.be/abc123"
        assert video_data["video_id"] == "abc123"
        assert isinstance(video_data["processed_date"], datetime)
    
    def test_transform_metadata_date_parsing(self):
        """Test proper date parsing from string to datetime."""
        json_metadata = {
            "task_id": "test-123",
            "title": "Test",
            "duration": 300,
            "uploader": "Test",
            "url": "https://youtu.be/test",
            "video_id": "test",
            "processed_date": "2024-01-15T10:30:45.123456"
        }
        
        video_data = transform_metadata(json_metadata)
        
        expected_date = datetime.fromisoformat("2024-01-15T10:30:45.123456")
        assert video_data["processed_date"] == expected_date
    
    def test_transform_metadata_handles_special_characters(self):
        """Test transformation handles unicode and special characters."""
        json_metadata = {
            "task_id": "test-123",
            "title": "Test Video with émojis 🎥 and spéçial chäracters",
            "duration": 300,
            "uploader": "Chännel with ñames",
            "url": "https://youtu.be/test",
            "video_id": "test",
            "processed_date": "2024-01-01T00:00:00.000000"
        }
        
        video_data = transform_metadata(json_metadata)
        
        assert "émojis 🎥" in video_data["title"]
        assert "spéçial chäracters" in video_data["title"]
        assert "Chännel with ñames" == video_data["uploader"]


class TestTranscriptProcessing:
    """Test transcript processing and chunking."""
    
    def test_process_transcript_basic_chunking(self):
        """Test basic transcript chunking into segments."""
        transcript = {
            "text": "First sentence. Second sentence with more words. Third sentence.",
            "words": [
                {"text": "First", "start": 0.0, "end": 0.5, "speaker_id": "speaker_0"},
                {"text": "sentence.", "start": 0.6, "end": 1.0, "speaker_id": "speaker_0"},
                {"text": "Second", "start": 1.5, "end": 2.0, "speaker_id": "speaker_0"},
                {"text": "sentence", "start": 2.1, "end": 2.5, "speaker_id": "speaker_0"},
                {"text": "with", "start": 2.6, "end": 2.8, "speaker_id": "speaker_0"},
                {"text": "more", "start": 2.9, "end": 3.2, "speaker_id": "speaker_0"},
                {"text": "words.", "start": 3.3, "end": 3.6, "speaker_id": "speaker_0"},
                {"text": "Third", "start": 4.0, "end": 4.3, "speaker_id": "speaker_1"},
                {"text": "sentence.", "start": 4.4, "end": 4.8, "speaker_id": "speaker_1"}
            ]
        }
        
        chunks = process_transcript(transcript, chunk_size_words=3)
        
        assert len(chunks) > 0
        # Should have multiple chunks since we have 9 words with chunk_size=3
        assert len(chunks) >= 3
        
        # Check first chunk
        first_chunk = chunks[0]
        assert first_chunk["start_ms"] == 0  # 0.0 seconds * 1000
        assert first_chunk["end_ms"] >= 1000  # Should end after 1.0 second
        assert "First sentence. Second" in first_chunk["text"]
        assert first_chunk["speaker_id"] == "speaker_0"
        assert first_chunk["word_count"] == 3
    
    def test_process_transcript_speaker_changes(self):
        """Test chunking respects speaker changes."""
        transcript = {
            "text": "Speaker zero talks. Then speaker one responds.",
            "words": [
                {"text": "Speaker", "start": 0.0, "end": 0.5, "speaker_id": "speaker_0"},
                {"text": "zero", "start": 0.6, "end": 0.9, "speaker_id": "speaker_0"},
                {"text": "talks.", "start": 1.0, "end": 1.3, "speaker_id": "speaker_0"},
                {"text": "Then", "start": 2.0, "end": 2.2, "speaker_id": "speaker_1"},
                {"text": "speaker", "start": 2.3, "end": 2.6, "speaker_id": "speaker_1"},
                {"text": "one", "start": 2.7, "end": 2.9, "speaker_id": "speaker_1"},
                {"text": "responds.", "start": 3.0, "end": 3.5, "speaker_id": "speaker_1"}
            ]
        }
        
        chunks = process_transcript(transcript, chunk_size_words=10)  # Large chunk size
        
        # Should create separate chunks for each speaker despite large chunk size
        assert len(chunks) >= 2
        
        speaker_0_chunk = next(chunk for chunk in chunks if chunk["speaker_id"] == "speaker_0")
        speaker_1_chunk = next(chunk for chunk in chunks if chunk["speaker_id"] == "speaker_1")
        
        assert "Speaker zero talks." in speaker_0_chunk["text"]
        assert "Then speaker one responds" in speaker_1_chunk["text"]
    
    def test_process_transcript_timestamps_conversion(self):
        """Test proper conversion of timestamps from seconds to milliseconds."""
        transcript = {
            "text": "Quick test.",
            "words": [
                {"text": "Quick", "start": 1.234, "end": 1.567, "speaker_id": "speaker_0"},
                {"text": "test.", "start": 1.890, "end": 2.123, "speaker_id": "speaker_0"}
            ]
        }
        
        chunks = process_transcript(transcript)
        
        assert len(chunks) == 1
        chunk = chunks[0]
        
        # 1.234 seconds = 1234 milliseconds
        assert chunk["start_ms"] == 1234
        # 2.123 seconds = 2123 milliseconds  
        assert chunk["end_ms"] == 2123
    
    def test_process_transcript_empty_words(self):
        """Test processing handles empty words array."""
        transcript = {
            "text": "Some text without word timing",
            "words": []
        }
        
        chunks = process_transcript(transcript)
        
        # Should still create one chunk with the full text
        assert len(chunks) == 1
        assert chunks[0]["text"] == "Some text without word timing"
        assert chunks[0]["start_ms"] == 0
        assert chunks[0]["end_ms"] == 0
        assert chunks[0]["speaker_id"] is None
        assert chunks[0]["word_count"] == 5  # Word count from text splitting


class TestSpeakerExtraction:
    """Test speaker identification and extraction."""
    
    def test_extract_speakers_single_speaker(self):
        """Test extraction with single speaker."""
        words = [
            {"text": "Hello", "speaker_id": "speaker_0"},
            {"text": "world", "speaker_id": "speaker_0"},
            {"text": "test", "speaker_id": "speaker_0"}
        ]
        
        speakers = extract_speakers(words)
        
        assert len(speakers) == 1
        assert speakers[0]["speaker_id"] == "speaker_0"
        assert speakers[0]["name"] is None
    
    def test_extract_speakers_multiple_speakers(self):
        """Test extraction with multiple speakers."""
        words = [
            {"text": "First", "speaker_id": "speaker_0"},
            {"text": "person", "speaker_id": "speaker_0"},
            {"text": "Second", "speaker_id": "speaker_1"},
            {"text": "person", "speaker_id": "speaker_1"},
            {"text": "Back", "speaker_id": "speaker_0"},
            {"text": "Third", "speaker_id": "speaker_2"}
        ]
        
        speakers = extract_speakers(words)
        
        assert len(speakers) == 3
        speaker_ids = [s["speaker_id"] for s in speakers]
        assert "speaker_0" in speaker_ids
        assert "speaker_1" in speaker_ids
        assert "speaker_2" in speaker_ids
    
    def test_extract_speakers_deduplication(self):
        """Test speakers are properly deduplicated."""
        words = [
            {"text": "Word1", "speaker_id": "speaker_0"},
            {"text": "Word2", "speaker_id": "speaker_1"},
            {"text": "Word3", "speaker_id": "speaker_0"},  # Duplicate
            {"text": "Word4", "speaker_id": "speaker_1"},  # Duplicate
            {"text": "Word5", "speaker_id": "speaker_0"}   # Duplicate
        ]
        
        speakers = extract_speakers(words)
        
        assert len(speakers) == 2  # Only unique speakers
        speaker_ids = [s["speaker_id"] for s in speakers]
        assert "speaker_0" in speaker_ids
        assert "speaker_1" in speaker_ids
    
    def test_extract_speakers_missing_speaker_id(self):
        """Test extraction handles words without speaker_id."""
        words = [
            {"text": "Word1", "speaker_id": "speaker_0"},
            {"text": "Word2"},  # Missing speaker_id
            {"text": "Word3", "speaker_id": "speaker_1"},
            {"text": "Word4", "speaker_id": None}  # Null speaker_id
        ]
        
        speakers = extract_speakers(words)
        
        # Should only extract defined speaker IDs
        assert len(speakers) == 2
        speaker_ids = [s["speaker_id"] for s in speakers]
        assert "speaker_0" in speaker_ids
        assert "speaker_1" in speaker_ids


class TestMigrationManager:
    """Test the main migration manager class."""
    
    def test_migration_manager_initialization(self):
        """Test MigrationManager initializes properly."""
        with tempfile.NamedTemporaryFile() as db_file:
            db_manager = init_database(f"sqlite:///{db_file.name}")
            
            manager = MigrationManager(
                videos_directory="/data/videos",
                database_manager=db_manager
            )
            
            assert manager.videos_directory == "/data/videos"
            assert manager.database_manager == db_manager
            assert manager.batch_size == 100  # Default batch size
            assert manager.chunk_size_words == 50  # Default chunk size
    
    def test_migration_manager_custom_parameters(self):
        """Test MigrationManager accepts custom parameters."""
        with tempfile.NamedTemporaryFile() as db_file:
            db_manager = init_database(f"sqlite:///{db_file.name}")
            
            manager = MigrationManager(
                videos_directory="/custom/path",
                database_manager=db_manager,
                batch_size=25,
                chunk_size_words=30
            )
            
            assert manager.videos_directory == "/custom/path"
            assert manager.batch_size == 25
            assert manager.chunk_size_words == 30
    
    @patch('app.migration.discover_video_data')
    def test_migration_manager_run_migration_no_data(self, mock_discover):
        """Test migration with no data to migrate."""
        with tempfile.NamedTemporaryFile() as db_file:
            db_manager = init_database(f"sqlite:///{db_file.name}")
            manager = MigrationManager("/data/videos", db_manager)
            
            mock_discover.return_value = []
            
            result = manager.run_migration()
            
            assert result["status"] == "success"
            assert result["videos_migrated"] == 0
            assert result["errors"] == []
            assert "No video data found" in result["message"]
    
    @patch('app.migration.discover_video_data')
    def test_migration_manager_run_migration_with_data(self, mock_discover):
        """Test migration processes discovered data."""
        with tempfile.NamedTemporaryFile() as db_file:
            db_manager = init_database(f"sqlite:///{db_file.name}")
            manager = MigrationManager("/data/videos", db_manager)
            
            # Mock discovered data
            mock_video_data = [{
                "task_id": "test-123",
                "metadata": {
                    "task_id": "test-123",
                    "title": "Test Video",
                    "duration": 300,
                    "uploader": "Test Channel",
                    "url": "https://youtu.be/test123",
                    "video_id": "test123",
                    "processed_date": "2024-01-01T00:00:00.000000"
                },
                "transcript": {
                    "text": "Hello world",
                    "words": [
                        {"text": "Hello", "start": 0.0, "end": 0.5, "speaker_id": "speaker_0"},
                        {"text": "world", "start": 0.6, "end": 1.0, "speaker_id": "speaker_0"}
                    ]
                }
            }]
            mock_discover.return_value = mock_video_data
            
            result = manager.run_migration()
            
            assert result["status"] == "success"
            assert result["videos_migrated"] == 1
            assert len(result["errors"]) == 0
            
            # Verify data was actually inserted
            with db_manager.get_session() as session:
                video = session.query(Video).filter(Video.id == "test-123").first()
                assert video is not None
                assert video.title == "Test Video"
                
                chunks = session.query(TranscriptChunk).filter(TranscriptChunk.video_id == "test-123").all()
                assert len(chunks) > 0
                
                speakers = session.query(Speaker).filter(Speaker.video_id == "test-123").all()
                assert len(speakers) == 1
                assert speakers[0].speaker_id == "speaker_0"
    
    def test_migration_manager_rollback_on_error(self):
        """Test migration rolls back on error."""
        with tempfile.NamedTemporaryFile() as db_file:
            db_manager = init_database(f"sqlite:///{db_file.name}")
            
            with patch('app.migration.discover_video_data') as mock_discover:
                # Mock data that will cause an error (invalid metadata)
                mock_video_data = [{
                    "task_id": "bad-data",
                    "metadata": {"task_id": "bad-data"},  # Missing required fields
                    "transcript": {"text": "test", "words": []}
                }]
                mock_discover.return_value = mock_video_data
                
                manager = MigrationManager("/data/videos", db_manager)
                result = manager.run_migration()
                
                assert result["status"] == "error"
                assert len(result["errors"]) > 0
                
                # Verify no partial data was saved
                with db_manager.get_session() as session:
                    videos = session.query(Video).all()
                    assert len(videos) == 0


class TestIntegrationTests:
    """Integration tests for the complete migration flow."""
    
    def test_end_to_end_migration_real_data_structure(self):
        """Test complete migration with realistic data structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            videos_dir = Path(temp_dir) / "videos"
            video_dir = videos_dir / "e1a792d7-3080-47d0-b199-8bccee31e555"
            video_dir.mkdir(parents=True)
            
            # Create realistic metadata (based on actual structure)
            metadata = {
                "task_id": "e1a792d7-3080-47d0-b199-8bccee31e555",
                "title": "22 Life-Changing Books Summarized in 28 Minutes",
                "duration": 1704,
                "uploader": "Mark Manson",
                "view_count": 50096,
                "upload_date": "20250817",
                "url": "https://youtu.be/3-pBWqbbmEA",
                "video_id": "3-pBWqbbmEA",
                "audio_file": f"{video_dir}/audio.webm",
                "processed_date": "2025-08-18T13:36:03.974979"
            }
            
            # Create realistic transcript (truncated for testing)
            transcript = {
                "language_code": "eng",
                "language_probability": 0.9888704419136047,
                "text": "You're busy, I'm busy, but we all wanna be smart and learn a lot of stuff.",
                "words": [
                    {"text": "You're", "start": 0.219, "end": 0.439, "type": "word", "speaker_id": "speaker_0", "logprob": 0.0},
                    {"text": " ", "start": 0.439, "end": 0.439, "type": "spacing", "speaker_id": "speaker_0", "logprob": 0.0},
                    {"text": "busy,", "start": 0.439, "end": 0.84, "type": "word", "speaker_id": "speaker_0", "logprob": 0.0},
                    {"text": " ", "start": 0.84, "end": 0.899, "type": "spacing", "speaker_id": "speaker_0", "logprob": 0.0},
                    {"text": "I'm", "start": 0.899, "end": 1.059, "type": "word", "speaker_id": "speaker_0", "logprob": 0.0},
                    {"text": " ", "start": 1.059, "end": 1.12, "type": "spacing", "speaker_id": "speaker_0", "logprob": 0.0},
                    {"text": "busy,", "start": 1.12, "end": 1.38, "type": "word", "speaker_id": "speaker_0", "logprob": 0.0}
                ]
            }
            
            # Write files
            with open(video_dir / "metadata.json", "w") as f:
                json.dump(metadata, f)
            with open(video_dir / "transcript.json", "w") as f:
                json.dump(transcript, f)
            
            # Run migration
            with tempfile.NamedTemporaryFile() as db_file:
                db_manager = init_database(f"sqlite:///{db_file.name}")
                manager = MigrationManager(str(videos_dir), db_manager)
                
                result = manager.run_migration()
                
                # Verify successful migration
                assert result["status"] == "success"
                assert result["videos_migrated"] == 1
                assert len(result["errors"]) == 0
                
                # Verify database content
                with db_manager.get_session() as session:
                    # Check video
                    video = session.query(Video).first()
                    assert video.id == "e1a792d7-3080-47d0-b199-8bccee31e555"
                    assert video.title == "22 Life-Changing Books Summarized in 28 Minutes"
                    assert video.duration == 1704
                    assert video.uploader == "Mark Manson"
                    
                    # Check transcript chunks
                    chunks = session.query(TranscriptChunk).all()
                    assert len(chunks) > 0
                    assert all(chunk.video_id == video.id for chunk in chunks)
                    
                    # Check speakers
                    speakers = session.query(Speaker).all()
                    assert len(speakers) == 1
                    assert speakers[0].speaker_id == "speaker_0"
                    assert speakers[0].video_id == video.id

    def test_migration_performance_metrics(self):
        """Test migration performance tracking."""
        with tempfile.NamedTemporaryFile() as db_file:
            db_manager = init_database(f"sqlite:///{db_file.name}")
            
            with patch('app.migration.discover_video_data') as mock_discover:
                mock_discover.return_value = []  # No data for quick test
                
                manager = MigrationManager("/data/videos", db_manager)
                
                import time
                start_time = time.time()
                result = manager.run_migration()
                end_time = time.time()
                
                # Should have performance metrics
                assert "performance" in result
                assert "duration_seconds" in result["performance"]
                assert result["performance"]["duration_seconds"] >= 0
                assert result["performance"]["duration_seconds"] <= (end_time - start_time) + 1  # Allow 1s buffer
    
    def test_migration_data_integrity_validation(self):
        """Test migration validates data integrity after insertion."""
        # This test should be implemented once the validation functions are created
        # For now, we'll mark it as a placeholder for the actual implementation
        pass


# Fixtures for common test data
@pytest.fixture
def sample_metadata():
    """Sample metadata for testing."""
    return {
        "task_id": "test-uuid-123",
        "title": "Test Video Title",
        "duration": 300,
        "uploader": "Test Channel",
        "url": "https://youtu.be/test123",
        "video_id": "test123",
        "processed_date": "2024-01-01T00:00:00.000000"
    }

@pytest.fixture
def sample_transcript():
    """Sample transcript for testing."""
    return {
        "text": "Hello world, this is a test transcript.",
        "language_code": "eng",
        "words": [
            {"text": "Hello", "start": 0.0, "end": 0.5, "speaker_id": "speaker_0"},
            {"text": "world,", "start": 0.6, "end": 1.0, "speaker_id": "speaker_0"},
            {"text": "this", "start": 1.1, "end": 1.3, "speaker_id": "speaker_0"},
            {"text": "is", "start": 1.4, "end": 1.6, "speaker_id": "speaker_0"},
            {"text": "a", "start": 1.7, "end": 1.8, "speaker_id": "speaker_0"},
            {"text": "test", "start": 1.9, "end": 2.2, "speaker_id": "speaker_1"},
            {"text": "transcript.", "start": 2.3, "end": 2.8, "speaker_id": "speaker_1"}
        ]
    }

@pytest.fixture
def temp_database():
    """Temporary database for testing."""
    with tempfile.NamedTemporaryFile() as db_file:
        db_manager = init_database(f"sqlite:///{db_file.name}")
        yield db_manager