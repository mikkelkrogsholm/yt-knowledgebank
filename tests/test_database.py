"""
Test suite for database infrastructure.
Following TDD approach - these tests should FAIL initially until implementation is complete.
"""
import pytest
import os
import tempfile
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import our database models and functions (these don't exist yet - will cause import errors)
from app.database import (
    DatabaseManager,
    Video,
    TranscriptChunk,
    Speaker,
    Base,
    init_database,
    get_database_session
)


class TestDatabaseConnection:
    """Test database connection creation and management."""
    
    def test_database_manager_creation(self):
        """Test that DatabaseManager can be created with SQLite."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db_url = f"sqlite:///{tmp_db.name}"
            db_manager = DatabaseManager(db_url)
            
            assert db_manager is not None
            assert db_manager.engine is not None
            
            # Cleanup
            os.unlink(tmp_db.name)
    
    def test_database_connection_pooling(self):
        """Test that database connection pooling is properly configured."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db_url = f"sqlite:///{tmp_db.name}"
            db_manager = DatabaseManager(db_url)
            
            # Test that we can create multiple sessions
            session1 = db_manager.get_session()
            session2 = db_manager.get_session()
            
            assert session1 is not None
            assert session2 is not None
            assert session1 != session2  # Different session instances
            
            session1.close()
            session2.close()
            
            # Cleanup
            os.unlink(tmp_db.name)
    
    def test_init_database_function(self):
        """Test the init_database function creates all tables."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db_url = f"sqlite:///{tmp_db.name}"
            
            # This should create all tables
            db_manager = init_database(db_url)
            
            # Check that tables exist by querying metadata
            inspector = db_manager.engine.dialect.has_table
            
            # Tables should exist
            assert inspector(db_manager.engine.connect(), "videos")
            assert inspector(db_manager.engine.connect(), "transcript_chunks") 
            assert inspector(db_manager.engine.connect(), "speakers")
            
            # Cleanup
            os.unlink(tmp_db.name)


class TestVideoModel:
    """Test the Video SQLAlchemy model."""
    
    @pytest.fixture
    def db_session(self):
        """Create a temporary database session for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db_url = f"sqlite:///{tmp_db.name}"
            db_manager = init_database(db_url)
            session = db_manager.get_session()
            
            yield session
            
            session.close()
            os.unlink(tmp_db.name)
    
    def test_video_model_creation(self, db_session):
        """Test creating a Video record."""
        video = Video(
            id="test-video-id",
            title="Test Video Title",
            duration=3600,  # 1 hour in seconds
            uploader="Test Channel",
            url="https://youtube.com/watch?v=test123",
            video_id="test123",
            processed_date=datetime.now()
        )
        
        db_session.add(video)
        db_session.commit()
        
        # Verify it was saved
        saved_video = db_session.query(Video).filter_by(id="test-video-id").first()
        assert saved_video is not None
        assert saved_video.title == "Test Video Title"
        assert saved_video.duration == 3600
        assert saved_video.video_id == "test123"
    
    def test_video_model_validation(self, db_session):
        """Test Video model field validation and constraints."""
        # Test required fields
        video = Video()  # Missing required fields should cause validation error
        
        with pytest.raises(Exception):  # Should fail validation
            db_session.add(video)
            db_session.commit()
    
    def test_video_model_relationships(self, db_session):
        """Test Video model relationships with transcript_chunks and speakers."""
        # Create a video
        video = Video(
            id="test-video-with-relations",
            title="Test Video With Relations",
            duration=1800,
            uploader="Test Channel",
            url="https://youtube.com/watch?v=relations123",
            video_id="relations123",
            processed_date=datetime.now()
        )
        db_session.add(video)
        
        # Create related transcript chunks
        chunk1 = TranscriptChunk(
            video_id="test-video-with-relations",
            start_ms=0,
            end_ms=5000,
            speaker_id="speaker_1",
            text="Hello world",
            word_count=2
        )
        
        chunk2 = TranscriptChunk(
            video_id="test-video-with-relations",
            start_ms=5000,
            end_ms=10000,
            speaker_id="speaker_2", 
            text="This is a test",
            word_count=4
        )
        
        db_session.add_all([chunk1, chunk2])
        
        # Create speakers
        speaker1 = Speaker(
            video_id="test-video-with-relations",
            speaker_id="speaker_1",
            name="John Doe"
        )
        
        speaker2 = Speaker(
            video_id="test-video-with-relations",
            speaker_id="speaker_2",
            name="Jane Smith"
        )
        
        db_session.add_all([speaker1, speaker2])
        db_session.commit()
        
        # Test relationships
        saved_video = db_session.query(Video).filter_by(id="test-video-with-relations").first()
        assert len(saved_video.transcript_chunks) == 2
        assert len(saved_video.speakers) == 2


class TestTranscriptChunkModel:
    """Test the TranscriptChunk SQLAlchemy model."""
    
    @pytest.fixture
    def db_session(self):
        """Create a temporary database session for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db_url = f"sqlite:///{tmp_db.name}"
            db_manager = init_database(db_url)
            session = db_manager.get_session()
            
            yield session
            
            session.close()
            os.unlink(tmp_db.name)
    
    def test_transcript_chunk_creation(self, db_session):
        """Test creating TranscriptChunk records."""
        # First create a video to reference
        video = Video(
            id="chunk-test-video",
            title="Chunk Test Video",
            duration=600,
            uploader="Test Channel",
            url="https://youtube.com/watch?v=chunk123",
            video_id="chunk123",
            processed_date=datetime.now()
        )
        db_session.add(video)
        
        # Create transcript chunk
        chunk = TranscriptChunk(
            video_id="chunk-test-video",
            start_ms=1000,
            end_ms=5000,
            speaker_id="speaker_test",
            text="This is a test transcript chunk",
            word_count=7
        )
        
        db_session.add(chunk)
        db_session.commit()
        
        # Verify it was saved
        saved_chunk = db_session.query(TranscriptChunk).filter_by(video_id="chunk-test-video").first()
        assert saved_chunk is not None
        assert saved_chunk.start_ms == 1000
        assert saved_chunk.end_ms == 5000
        assert saved_chunk.text == "This is a test transcript chunk"
        assert saved_chunk.word_count == 7
    
    def test_transcript_chunk_ordering(self, db_session):
        """Test that transcript chunks can be ordered by timestamp."""
        # Create video
        video = Video(
            id="ordering-test-video",
            title="Ordering Test Video",
            duration=600,
            uploader="Test Channel", 
            url="https://youtube.com/watch?v=ordering123",
            video_id="ordering123",
            processed_date=datetime.now()
        )
        db_session.add(video)
        
        # Create chunks in random order
        chunks = [
            TranscriptChunk(video_id="ordering-test-video", start_ms=5000, end_ms=10000, speaker_id="s1", text="Second", word_count=1),
            TranscriptChunk(video_id="ordering-test-video", start_ms=0, end_ms=5000, speaker_id="s1", text="First", word_count=1),
            TranscriptChunk(video_id="ordering-test-video", start_ms=10000, end_ms=15000, speaker_id="s1", text="Third", word_count=1),
        ]
        
        db_session.add_all(chunks)
        db_session.commit()
        
        # Query ordered by start_ms
        ordered_chunks = db_session.query(TranscriptChunk)\
            .filter_by(video_id="ordering-test-video")\
            .order_by(TranscriptChunk.start_ms)\
            .all()
        
        assert len(ordered_chunks) == 3
        assert ordered_chunks[0].text == "First"
        assert ordered_chunks[1].text == "Second" 
        assert ordered_chunks[2].text == "Third"


class TestSpeakerModel:
    """Test the Speaker SQLAlchemy model."""
    
    @pytest.fixture
    def db_session(self):
        """Create a temporary database session for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db_url = f"sqlite:///{tmp_db.name}"
            db_manager = init_database(db_url)
            session = db_manager.get_session()
            
            yield session
            
            session.close()
            os.unlink(tmp_db.name)
    
    def test_speaker_creation(self, db_session):
        """Test creating Speaker records."""
        # Create video first
        video = Video(
            id="speaker-test-video",
            title="Speaker Test Video",
            duration=600,
            uploader="Test Channel",
            url="https://youtube.com/watch?v=speaker123",
            video_id="speaker123",
            processed_date=datetime.now()
        )
        db_session.add(video)
        
        # Create speaker
        speaker = Speaker(
            video_id="speaker-test-video",
            speaker_id="speaker_001",
            name="Test Speaker"
        )
        
        db_session.add(speaker)
        db_session.commit()
        
        # Verify it was saved
        saved_speaker = db_session.query(Speaker).filter_by(video_id="speaker-test-video").first()
        assert saved_speaker is not None
        assert saved_speaker.speaker_id == "speaker_001"
        assert saved_speaker.name == "Test Speaker"
    
    def test_speaker_unique_constraints(self, db_session):
        """Test that speakers have proper unique constraints per video."""
        # Create video
        video = Video(
            id="unique-speaker-test-video",
            title="Unique Speaker Test Video", 
            duration=600,
            uploader="Test Channel",
            url="https://youtube.com/watch?v=unique123",
            video_id="unique123",
            processed_date=datetime.now()
        )
        db_session.add(video)
        
        # Create first speaker
        speaker1 = Speaker(
            video_id="unique-speaker-test-video",
            speaker_id="speaker_duplicate",
            name="First Speaker"
        )
        db_session.add(speaker1)
        db_session.commit()
        
        # Try to create duplicate speaker_id for same video (should fail)
        speaker2 = Speaker(
            video_id="unique-speaker-test-video", 
            speaker_id="speaker_duplicate",  # Same speaker_id
            name="Duplicate Speaker"
        )
        
        db_session.add(speaker2)
        
        with pytest.raises(Exception):  # Should fail due to unique constraint
            db_session.commit()


class TestDatabaseCRUD:
    """Test basic CRUD operations across all models."""
    
    @pytest.fixture
    def db_session(self):
        """Create a temporary database session for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db_url = f"sqlite:///{tmp_db.name}"
            db_manager = init_database(db_url)
            session = db_manager.get_session()
            
            yield session
            
            session.close()
            os.unlink(tmp_db.name)
    
    def test_full_video_data_crud(self, db_session):
        """Test complete CRUD operations for a video with all related data."""
        
        # CREATE
        video = Video(
            id="crud-test-video",
            title="CRUD Test Video",
            duration=1200,
            uploader="CRUD Channel",
            url="https://youtube.com/watch?v=crud123",
            video_id="crud123", 
            processed_date=datetime.now()
        )
        
        speakers = [
            Speaker(video_id="crud-test-video", speaker_id="speaker_1", name="Alice"),
            Speaker(video_id="crud-test-video", speaker_id="speaker_2", name="Bob")
        ]
        
        chunks = [
            TranscriptChunk(video_id="crud-test-video", start_ms=0, end_ms=3000, speaker_id="speaker_1", text="Hello from Alice", word_count=3),
            TranscriptChunk(video_id="crud-test-video", start_ms=3000, end_ms=6000, speaker_id="speaker_2", text="Hello from Bob", word_count=3),
        ]
        
        db_session.add(video)
        db_session.add_all(speakers)
        db_session.add_all(chunks)
        db_session.commit()
        
        # READ
        saved_video = db_session.query(Video).filter_by(id="crud-test-video").first()
        assert saved_video is not None
        assert len(saved_video.speakers) == 2
        assert len(saved_video.transcript_chunks) == 2
        
        # UPDATE
        saved_video.title = "Updated CRUD Test Video"
        db_session.commit()
        
        updated_video = db_session.query(Video).filter_by(id="crud-test-video").first()
        assert updated_video.title == "Updated CRUD Test Video"
        
        # DELETE
        db_session.delete(saved_video)
        db_session.commit()
        
        deleted_video = db_session.query(Video).filter_by(id="crud-test-video").first()
        assert deleted_video is None
        
        # Related records should also be handled (cascade delete)
        remaining_speakers = db_session.query(Speaker).filter_by(video_id="crud-test-video").all()
        remaining_chunks = db_session.query(TranscriptChunk).filter_by(video_id="crud-test-video").all()
        
        # Depending on cascade settings, these should be empty
        assert len(remaining_speakers) == 0
        assert len(remaining_chunks) == 0


class TestDatabaseSession:
    """Test database session management functions."""
    
    def test_get_database_session_function(self):
        """Test the get_database_session helper function."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db_url = f"sqlite:///{tmp_db.name}"
            
            # Initialize database
            init_database(db_url)
            
            # Get session using helper function
            session = get_database_session()
            
            assert session is not None
            
            # Should be able to query
            videos = session.query(Video).all()
            assert isinstance(videos, list)
            
            session.close()
            
            # Cleanup
            os.unlink(tmp_db.name)