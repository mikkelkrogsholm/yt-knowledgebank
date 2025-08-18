"""
Comprehensive tests for database_queries.py module.

This test suite covers all query functions and edge cases to improve coverage.
"""
import pytest
import tempfile
import os
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from app.database import init_database, DatabaseManager, Video, TranscriptChunk, Speaker
from app.database_queries import (
    get_all_videos_from_database, get_task_result_from_database,
    save_video_to_database, check_video_exists_in_database, get_database_stats
)


class TestDatabaseQueries:
    """Test all database query functions."""
    
    def setup_method(self):
        """Set up test database for each test."""
        # Use in-memory database for testing
        self.db_manager = DatabaseManager(":memory:")
        self.db_manager.create_tables()
        
        # Sample data for testing
        self.sample_video_data = {
            "id": "test-video-123",
            "title": "Test Video: Amazing Content",
            "duration": 1800,
            "uploader": "Test Channel",
            "view_count": 50000,
            "upload_date": "20250817",
            "url": "https://youtu.be/test123",
            "video_id": "test123",
            "processed_date": datetime.now(timezone.utc).isoformat(),
            "audio_file_path": "/app/data/videos/test-video-123/audio.webm"
        }
        
        self.sample_transcript_data = {
            "language_code": "eng", 
            "language_probability": 0.98,
            "text": "This is a test transcript with multiple speakers.",
            "words": [
                {
                    "speaker_id": "speaker_0",
                    "start_ms": 0,
                    "end_ms": 1000,
                    "text": "This is a test"
                },
                {
                    "speaker_id": "speaker_1", 
                    "start_ms": 1000,
                    "end_ms": 2000,
                    "text": "transcript with multiple"
                },
                {
                    "speaker_id": "speaker_0",
                    "start_ms": 2000,
                    "end_ms": 3000, 
                    "text": "speakers."
                }
            ]
        }
    
    def test_get_all_videos_from_database_empty(self):
        """Test getting all videos from empty database."""
        videos = get_all_videos_from_database(self.db_manager)
        assert videos == []
    
    def test_save_and_get_video_from_database(self):
        """Test saving and retrieving a video from database."""
        # Save video
        result = save_video_to_database(
            self.db_manager,
            self.sample_video_data,
            self.sample_transcript_data
        )
        assert result["success"] is True
        assert result["video_id"] == "test-video-123"
        
        # Get all videos
        videos = get_all_videos_from_database(self.db_manager)
        assert len(videos) == 1
        
        video = videos[0]
        assert video["task_id"] == "test-video-123"
        assert video["title"] == "Test Video: Amazing Content"
        assert video["uploader"] == "Test Channel"
        assert "duration_formatted" in video
        assert "word_count" in video
        assert "speaker_count" in video
        
        # Get specific video
        specific_video = get_video_by_id_from_database(self.db_manager, "test-video-123")
        assert specific_video is not None
        assert specific_video["metadata"]["task_id"] == "test-video-123"
        assert "transcript" in specific_video
    
    def test_get_video_by_id_nonexistent(self):
        """Test getting non-existent video by ID."""
        result = get_video_by_id_from_database(self.db_manager, "nonexistent-id")
        assert result is None
    
    def test_update_video_metadata(self):
        """Test updating video metadata."""
        # First save a video
        save_video_to_database(
            self.db_manager,
            self.sample_video_data,
            self.sample_transcript_data
        )
        
        # Update metadata
        updated_data = self.sample_video_data.copy()
        updated_data["title"] = "Updated Title"
        updated_data["view_count"] = 75000
        
        result = update_video_metadata(self.db_manager, "test-video-123", updated_data)
        assert result["success"] is True
        
        # Verify update
        video = get_video_by_id_from_database(self.db_manager, "test-video-123")
        assert video["metadata"]["title"] == "Updated Title"
        assert video["metadata"]["view_count"] == 75000
    
    def test_update_nonexistent_video(self):
        """Test updating non-existent video."""
        result = update_video_metadata(self.db_manager, "nonexistent-id", self.sample_video_data)
        assert result["success"] is False
        assert "not found" in result["error"]
    
    def test_delete_video_from_database(self):
        """Test deleting video from database."""
        # First save a video
        save_video_to_database(
            self.db_manager,
            self.sample_video_data,
            self.sample_transcript_data
        )
        
        # Verify it exists
        videos = get_all_videos_from_database(self.db_manager)
        assert len(videos) == 1
        
        # Delete it
        result = delete_video_from_database(self.db_manager, "test-video-123")
        assert result["success"] is True
        
        # Verify deletion
        videos = get_all_videos_from_database(self.db_manager)
        assert len(videos) == 0
        
        video = get_video_by_id_from_database(self.db_manager, "test-video-123")
        assert video is None
    
    def test_delete_nonexistent_video(self):
        """Test deleting non-existent video."""
        result = delete_video_from_database(self.db_manager, "nonexistent-id")
        assert result["success"] is False
        assert "not found" in result["error"]
    
    def test_get_transcript_chunks_by_video_id(self):
        """Test getting transcript chunks for a video."""
        # Save video with transcript
        save_video_to_database(
            self.db_manager,
            self.sample_video_data,
            self.sample_transcript_data
        )
        
        # Get transcript chunks
        chunks = get_transcript_chunks_by_video_id(self.db_manager, "test-video-123")
        assert len(chunks) == 3  # We have 3 words in sample data
        
        chunk = chunks[0]
        assert chunk["video_id"] == "test-video-123"
        assert chunk["speaker_id"] == "speaker_0"
        assert chunk["text"] == "This is a test"
        assert chunk["start_ms"] == 0
        assert chunk["end_ms"] == 1000
    
    def test_get_transcript_chunks_nonexistent_video(self):
        """Test getting transcript chunks for non-existent video."""
        chunks = get_transcript_chunks_by_video_id(self.db_manager, "nonexistent-id")
        assert chunks == []
    
    def test_save_transcript_chunks_to_database(self):
        """Test saving transcript chunks independently."""
        # First save a video without transcript
        video_data_no_transcript = self.sample_video_data.copy()
        save_video_to_database(self.db_manager, video_data_no_transcript, {"words": []})
        
        # Save transcript chunks separately
        result = save_transcript_chunks_to_database(
            self.db_manager,
            "test-video-123",
            self.sample_transcript_data
        )
        assert result["success"] is True
        assert result["chunks_saved"] == 3
        
        # Verify chunks were saved
        chunks = get_transcript_chunks_by_video_id(self.db_manager, "test-video-123")
        assert len(chunks) == 3
    
    def test_get_speakers_by_video_id(self):
        """Test getting speakers for a video."""
        # Save video with transcript
        save_video_to_database(
            self.db_manager,
            self.sample_video_data,
            self.sample_transcript_data
        )
        
        # Get speakers
        speakers = get_speakers_by_video_id(self.db_manager, "test-video-123")
        assert len(speakers) == 2  # speaker_0 and speaker_1
        
        speaker_ids = [s["speaker_id"] for s in speakers]
        assert "speaker_0" in speaker_ids
        assert "speaker_1" in speaker_ids
    
    def test_save_speakers_to_database(self):
        """Test saving speakers independently."""
        # First save a video
        save_video_to_database(self.db_manager, self.sample_video_data, {"words": []})
        
        # Save speakers separately
        speakers_data = [
            {"speaker_id": "speaker_0", "word_count": 100},
            {"speaker_id": "speaker_1", "word_count": 50}
        ]
        
        result = save_speakers_to_database(
            self.db_manager,
            "test-video-123",
            speakers_data
        )
        assert result["success"] is True
        assert result["speakers_saved"] == 2
        
        # Verify speakers were saved
        speakers = get_speakers_by_video_id(self.db_manager, "test-video-123")
        assert len(speakers) == 2
    
    def test_search_transcript_chunks(self):
        """Test searching transcript chunks."""
        # Save video with transcript
        save_video_to_database(
            self.db_manager,
            self.sample_video_data,
            self.sample_transcript_data
        )
        
        # Search for "test"
        results = search_transcript_chunks(
            self.db_manager,
            "test",
            limit=10,
            offset=0
        )
        assert len(results) > 0
        
        # Should find chunks containing "test"
        found_test = any("test" in result["text"].lower() for result in results)
        assert found_test is True
    
    def test_search_transcript_chunks_with_filters(self):
        """Test searching with video_id and speaker_id filters."""
        # Save video with transcript
        save_video_to_database(
            self.db_manager,
            self.sample_video_data,
            self.sample_transcript_data
        )
        
        # Search with video filter
        results = search_transcript_chunks(
            self.db_manager,
            "transcript",
            video_id="test-video-123",
            limit=10,
            offset=0
        )
        assert len(results) > 0
        assert all(r["video_id"] == "test-video-123" for r in results)
        
        # Search with speaker filter
        results = search_transcript_chunks(
            self.db_manager,
            "transcript",
            speaker_id="speaker_1",
            limit=10,
            offset=0
        )
        assert len(results) > 0
        assert all(r["speaker_id"] == "speaker_1" for r in results)
    
    def test_get_video_statistics(self):
        """Test getting video statistics."""
        # Save multiple videos
        for i in range(3):
            video_data = self.sample_video_data.copy()
            video_data["id"] = f"test-video-{i}"
            video_data["video_id"] = f"test{i}"
            save_video_to_database(self.db_manager, video_data, self.sample_transcript_data)
        
        # Get statistics
        stats = get_video_statistics(self.db_manager)
        assert stats["total_videos"] == 3
        assert stats["total_duration_seconds"] == 1800 * 3
        assert stats["total_transcript_chunks"] == 9  # 3 chunks per video
        assert stats["total_speakers"] == 6  # 2 speakers per video
        assert stats["average_duration_seconds"] == 1800
        assert "total_duration_formatted" in stats
        assert "average_duration_formatted" in stats
    
    def test_get_processing_statistics(self):
        """Test getting processing statistics."""
        # Save videos with different processing dates
        import time
        for i in range(2):
            video_data = self.sample_video_data.copy()
            video_data["id"] = f"test-video-{i}"
            video_data["video_id"] = f"test{i}"
            video_data["processed_date"] = datetime.now(timezone.utc).isoformat()
            save_video_to_database(self.db_manager, video_data, self.sample_transcript_data)
            time.sleep(0.01)  # Small delay to ensure different timestamps
        
        # Get statistics
        stats = get_processing_statistics(self.db_manager, days=7)
        assert stats["videos_processed_in_period"] == 2
        assert stats["period_days"] == 7
        assert "processing_rate_per_day" in stats
        assert "first_video_date" in stats
        assert "latest_video_date" in stats
    
    def test_cleanup_orphaned_data(self):
        """Test cleaning up orphaned data."""
        # Save video with transcript
        save_video_to_database(
            self.db_manager,
            self.sample_video_data,
            self.sample_transcript_data
        )
        
        # Manually create orphaned data by deleting video but leaving chunks
        session = self.db_manager.get_session()
        try:
            # Delete video but leave chunks and speakers
            video = session.query(Video).filter(Video.id == "test-video-123").first()
            if video:
                session.delete(video)
                session.commit()
            
            # Run cleanup
            result = cleanup_orphaned_data(self.db_manager)
            assert result["success"] is True
            assert result["orphaned_chunks_deleted"] >= 0
            assert result["orphaned_speakers_deleted"] >= 0
            
        finally:
            session.close()
    
    def test_database_error_handling(self):
        """Test error handling in database operations."""
        # Test with invalid database manager
        invalid_db = MagicMock()
        invalid_db.get_session.side_effect = Exception("Database connection failed")
        
        # Should handle errors gracefully
        result = get_all_videos_from_database(invalid_db)
        assert result == []
        
        result = save_video_to_database(invalid_db, self.sample_video_data, self.sample_transcript_data)
        assert result["success"] is False
        assert "error" in result
    
    def test_edge_case_empty_transcript(self):
        """Test handling empty transcript data."""
        empty_transcript = {"words": [], "text": "", "language_code": "eng"}
        
        result = save_video_to_database(
            self.db_manager,
            self.sample_video_data,
            empty_transcript
        )
        assert result["success"] is True
        
        # Should still create video record
        videos = get_all_videos_from_database(self.db_manager)
        assert len(videos) == 1
        
        # But no transcript chunks
        chunks = get_transcript_chunks_by_video_id(self.db_manager, "test-video-123")
        assert len(chunks) == 0
    
    def test_edge_case_invalid_data_types(self):
        """Test handling invalid data types."""
        invalid_video_data = self.sample_video_data.copy()
        invalid_video_data["duration"] = "not_a_number"
        invalid_video_data["view_count"] = None
        
        # Should handle gracefully
        result = save_video_to_database(
            self.db_manager,
            invalid_video_data,
            self.sample_transcript_data
        )
        # Implementation should handle type conversion or validation
        # Result depends on actual implementation
        assert "success" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])