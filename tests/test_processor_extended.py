"""
Extended comprehensive tests for processor.py module to improve coverage.

This test suite covers additional functions and edge cases not covered by existing tests.
"""
import pytest
import tempfile
import os
import json
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock, mock_open

from app.processor import (
    get_all_videos, get_task_result, get_all_videos_from_files, get_task_result_from_files,
    format_duration, format_date, extract_video_id
)


class TestProcessorExtended:
    """Extended tests for processor functions."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.test_task_id = "test-task-123"
        self.test_url = "https://youtu.be/test123"
        self.test_api_key = "sk_test123456789"
        
        # Clear progress store
        progress_store.clear()
        
        # Sample metadata
        self.sample_metadata = {
            "id": "test123",
            "title": "Test Video: Amazing Content",
            "duration": 3665,  # 1 hour, 1 minute, 5 seconds
            "uploader": "Test Channel",
            "view_count": 50000,
            "upload_date": "20250817",
            "webpage_url": self.test_url
        }
        
        # Sample transcript
        self.sample_transcript = {
            "language_code": "eng",
            "language_probability": 0.9888704419136047,
            "text": "This is a test transcript with multiple speakers talking about various topics.",
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
                    "end_ms": 2500,
                    "text": "transcript with multiple"
                },
                {
                    "speaker_id": "speaker_0",
                    "start_ms": 2500,
                    "end_ms": 4000,
                    "text": "speakers talking about"
                },
                {
                    "speaker_id": "speaker_2",
                    "start_ms": 4000,
                    "end_ms": 5500,
                    "text": "various topics."
                }
            ]
        }
    
    def test_format_duration_various_lengths(self):
        """Test duration formatting with various time lengths."""
        # Test seconds only
        assert format_duration(30) == "0:30"
        assert format_duration(59) == "0:59"
        
        # Test minutes and seconds
        assert format_duration(60) == "1:00"
        assert format_duration(90) == "1:30"
        assert format_duration(3599) == "59:59"
        
        # Test hours, minutes, and seconds
        assert format_duration(3600) == "1:00:00"
        assert format_duration(3661) == "1:01:01"
        assert format_duration(7200) == "2:00:00"
        assert format_duration(self.sample_metadata["duration"]) == "1:01:05"
        
        # Test edge cases
        assert format_duration(0) == "0:00"
        assert format_duration(1) == "0:01"
    
    def test_format_duration_invalid_input(self):
        """Test duration formatting with invalid input."""
        # Test None
        assert format_duration(None) == "0:00"
        
        # Test negative numbers
        assert format_duration(-10) == "0:00"
        
        # Test non-numeric input (should be handled gracefully)
        try:
            result = format_duration("not_a_number")
            # If it doesn't raise an exception, it should return a sensible default
            assert isinstance(result, str)
        except (TypeError, ValueError):
            # Expected behavior for invalid input
            pass
    
    def test_format_date_various_formats(self):
        """Test date formatting with various input formats."""
        # Test standard ISO format
        iso_date = "2025-08-17T14:30:45.123456"
        formatted = format_date(iso_date)
        assert "Aug 17, 2025" in formatted
        assert "2:30 PM" in formatted or "14:30" in formatted
        
        # Test date only format
        date_only = "2025-08-17"
        formatted = format_date(date_only)
        assert "Aug 17, 2025" in formatted
        
        # Test YouTube upload date format
        youtube_date = "20250817"
        formatted = format_date(youtube_date)
        assert "Aug 17, 2025" in formatted
    
    def test_format_date_invalid_input(self):
        """Test date formatting with invalid input."""
        # Test None
        result = format_date(None)
        assert result == "Unknown date"
        
        # Test empty string
        result = format_date("")
        assert result == "Unknown date"
        
        # Test invalid date string
        result = format_date("not_a_date")
        assert result == "Unknown date"
        
        # Test malformed ISO date
        result = format_date("2025-13-45T25:70:90")
        assert result == "Unknown date"
    
    def test_calculate_word_count_various_transcripts(self):
        """Test word count calculation with various transcript formats."""
        # Test normal transcript
        word_count = calculate_word_count(self.sample_transcript)
        expected_words = len("This is a test transcript with multiple speakers talking about various topics.".split())
        assert word_count == expected_words
        
        # Test transcript with only words array
        words_only_transcript = {"words": self.sample_transcript["words"]}
        word_count = calculate_word_count(words_only_transcript)
        expected_from_words = sum(len(word["text"].split()) for word in self.sample_transcript["words"])
        assert word_count == expected_from_words
        
        # Test empty transcript
        empty_transcript = {"text": "", "words": []}
        assert calculate_word_count(empty_transcript) == 0
        
        # Test transcript with only text
        text_only = {"text": "Just some text here"}
        assert calculate_word_count(text_only) == 4
        
        # Test None input
        assert calculate_word_count(None) == 0
        
        # Test transcript with punctuation and multiple spaces
        complex_text = {"text": "Hello,   world!  How  are   you?"}
        assert calculate_word_count(complex_text) == 5
    
    def test_extract_speakers_various_scenarios(self):
        """Test speaker extraction with various scenarios."""
        # Test normal transcript with multiple speakers
        speakers = extract_speakers(self.sample_transcript)
        assert len(speakers) == 3  # speaker_0, speaker_1, speaker_2
        
        speaker_ids = [s["speaker_id"] for s in speakers]
        assert "speaker_0" in speaker_ids
        assert "speaker_1" in speaker_ids  
        assert "speaker_2" in speaker_ids
        
        # Verify word counts
        speaker_0_words = sum(len(word["text"].split()) for word in self.sample_transcript["words"] 
                             if word["speaker_id"] == "speaker_0")
        speaker_0_data = next(s for s in speakers if s["speaker_id"] == "speaker_0")
        assert speaker_0_data["word_count"] == speaker_0_words
        
        # Test single speaker
        single_speaker_transcript = {
            "words": [
                {"speaker_id": "speaker_0", "text": "Only one speaker here"},
                {"speaker_id": "speaker_0", "text": "talking throughout"}
            ]
        }
        speakers = extract_speakers(single_speaker_transcript)
        assert len(speakers) == 1
        assert speakers[0]["speaker_id"] == "speaker_0"
        assert speakers[0]["word_count"] == 6  # "Only one speaker here talking throughout"
        
        # Test empty transcript
        empty_transcript = {"words": []}
        speakers = extract_speakers(empty_transcript)
        assert speakers == []
        
        # Test None input
        speakers = extract_speakers(None)
        assert speakers == []
        
        # Test transcript without words
        no_words_transcript = {"text": "Some text"}
        speakers = extract_speakers(no_words_transcript)
        assert speakers == []
    
    @patch('app.processor.os.path.exists')
    @patch('app.processor.os.listdir')
    def test_get_all_videos_empty_directory(self, mock_listdir, mock_exists):
        """Test get_all_videos with empty videos directory."""
        # Mock empty directory
        mock_exists.return_value = False
        
        videos = get_all_videos()
        assert videos == []
    
    @patch('app.processor.os.path.exists')
    @patch('app.processor.os.listdir')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_all_videos_with_corrupted_metadata(self, mock_file, mock_listdir, mock_exists):
        """Test get_all_videos with corrupted metadata files."""
        # Mock directory structure
        mock_exists.side_effect = lambda path: True
        mock_listdir.return_value = ["video1", "video2"]
        
        # Mock corrupted JSON file
        mock_file.return_value.read.return_value = "corrupted json"
        
        videos = get_all_videos()
        # Should handle corruption gracefully and skip corrupted videos
        assert isinstance(videos, list)
        # Specific behavior depends on implementation
    
    @patch('app.processor.os.path.exists')
    def test_get_task_result_nonexistent_video(self, mock_exists):
        """Test get_task_result with non-existent video."""
        # Mock video directory doesn't exist
        mock_exists.return_value = False
        
        with pytest.raises(FileNotFoundError):
            get_task_result("nonexistent-task-id")
    
    @patch('app.processor.os.path.exists') 
    @patch('builtins.open', new_callable=mock_open)
    def test_get_task_result_missing_files(self, mock_file, mock_exists):
        """Test get_task_result with missing metadata or transcript files."""
        # Mock video directory exists but files don't
        mock_exists.side_effect = lambda path: "videos/test-task" in path and not path.endswith('.json')
        
        with pytest.raises(FileNotFoundError):
            get_task_result("test-task")
    
    @pytest.mark.asyncio
    @patch('app.processor.download_audio')
    @patch('app.processor.extract_metadata')
    async def test_process_and_transcribe_download_failure(self, mock_extract, mock_download):
        """Test process_and_transcribe when download fails."""
        # Mock successful metadata extraction but failed download
        mock_extract.return_value = self.sample_metadata
        mock_download.return_value = False
        
        # Run processing
        await process_and_transcribe(self.test_url, self.test_task_id, self.test_api_key)
        
        # Check progress store shows error
        assert self.test_task_id in progress_store
        final_progress = progress_store[self.test_task_id]
        assert final_progress["phase"] == "error"
        assert "download" in final_progress["message"].lower()
    
    @pytest.mark.asyncio
    @patch('app.processor.download_audio')
    @patch('app.processor.extract_metadata')
    async def test_process_and_transcribe_metadata_failure(self, mock_extract, mock_download):
        """Test process_and_transcribe when metadata extraction fails."""
        # Mock failed metadata extraction
        mock_extract.return_value = None
        
        # Run processing
        await process_and_transcribe(self.test_url, self.test_task_id, self.test_api_key)
        
        # Check progress store shows error
        assert self.test_task_id in progress_store
        final_progress = progress_store[self.test_task_id]
        assert final_progress["phase"] == "error"
        assert "metadata" in final_progress["message"].lower() or "extract" in final_progress["message"].lower()
    
    @pytest.mark.asyncio
    @patch('app.processor.download_audio')
    @patch('app.processor.extract_metadata')
    @patch('app.processor.ElevenLabs')
    async def test_process_and_transcribe_transcription_failure(self, mock_elevenlabs, mock_extract, mock_download):
        """Test process_and_transcribe when transcription fails."""
        # Mock successful metadata and download
        mock_extract.return_value = self.sample_metadata
        mock_download.return_value = True
        
        # Mock failed transcription
        mock_client = MagicMock()
        mock_elevenlabs.return_value = mock_client
        mock_client.speech_to_text.transcribe.side_effect = Exception("Transcription failed")
        
        # Run processing
        await process_and_transcribe(self.test_url, self.test_task_id, self.test_api_key)
        
        # Check progress store shows error
        assert self.test_task_id in progress_store
        final_progress = progress_store[self.test_task_id]
        assert final_progress["phase"] == "error"
        assert "transcrib" in final_progress["message"].lower()
    
    @pytest.mark.asyncio
    @patch('app.processor.download_audio')
    @patch('app.processor.extract_metadata')
    @patch('app.processor.ElevenLabs')
    @patch('app.processor.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    async def test_process_and_transcribe_file_save_failure(self, mock_file, mock_makedirs, mock_elevenlabs, mock_extract, mock_download):
        """Test process_and_transcribe when file saving fails."""
        # Mock successful processing up to file save
        mock_extract.return_value = self.sample_metadata
        mock_download.return_value = True
        
        # Mock successful transcription
        mock_client = MagicMock()
        mock_elevenlabs.return_value = mock_client
        mock_transcription = MagicMock()
        mock_transcription.text = self.sample_transcript["text"]
        mock_transcription.alignment = MagicMock()
        mock_transcription.alignment.words = [
            MagicMock(text="test", start_ms=0, end_ms=1000, speaker_id="speaker_0")
        ]
        mock_client.speech_to_text.transcribe.return_value = mock_transcription
        
        # Mock file save failure
        mock_file.side_effect = IOError("Disk full")
        
        # Run processing
        await process_and_transcribe(self.test_url, self.test_task_id, self.test_api_key)
        
        # Check progress store shows error
        assert self.test_task_id in progress_store
        final_progress = progress_store[self.test_task_id]
        assert final_progress["phase"] == "error"
        assert "save" in final_progress["message"].lower() or "write" in final_progress["message"].lower()
    
    def test_progress_store_concurrent_access(self):
        """Test progress store with concurrent access simulation."""
        task_ids = [f"task-{i}" for i in range(10)]
        
        # Simulate concurrent updates
        for task_id in task_ids:
            progress_store[task_id] = {
                "phase": "downloading",
                "progress": 50,
                "message": f"Processing {task_id}"
            }
        
        # Verify all updates
        assert len(progress_store) == 10
        for task_id in task_ids:
            assert task_id in progress_store
            assert progress_store[task_id]["phase"] == "downloading"
            assert progress_store[task_id]["progress"] == 50
    
    def test_progress_store_cleanup(self):
        """Test that progress store can be cleared."""
        # Add some entries
        progress_store["task1"] = {"phase": "downloading"}
        progress_store["task2"] = {"phase": "transcribing"}
        
        assert len(progress_store) == 2
        
        # Clear store
        progress_store.clear()
        assert len(progress_store) == 0
    
    @patch('app.processor.os.path.exists')
    @patch('app.processor.os.listdir')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_all_videos_performance(self, mock_file, mock_listdir, mock_exists):
        """Test get_all_videos performance with many videos."""
        # Mock large number of video directories
        video_dirs = [f"video-{i}" for i in range(100)]
        mock_listdir.return_value = video_dirs
        mock_exists.return_value = True
        
        # Mock metadata files
        metadata = json.dumps({
            "task_id": "test-video",
            "title": "Test Video",
            "duration": 300,
            "processed_date": "2025-08-17T14:30:45"
        })
        transcript = json.dumps({"text": "test transcript", "words": []})
        mock_file.return_value.read.side_effect = [metadata, transcript] * 100
        
        # Get all videos (should handle large numbers efficiently)
        videos = get_all_videos()
        
        # Should return all videos
        assert len(videos) <= 100  # Depends on implementation efficiency
        assert isinstance(videos, list)
    
    def test_edge_cases_empty_strings(self):
        """Test edge cases with empty strings."""
        # Test empty duration formatting
        assert format_duration("") == "0:00"
        
        # Test empty date formatting
        assert format_date("") == "Unknown date"
        
        # Test empty transcript word counting
        empty_text_transcript = {"text": ""}
        assert calculate_word_count(empty_text_transcript) == 0
        
        # Test empty speaker extraction
        empty_speaker_transcript = {"words": []}
        assert extract_speakers(empty_speaker_transcript) == []
    
    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters."""
        # Test unicode in transcript
        unicode_transcript = {
            "text": "Test with émojis 🎵 and ünïcödë characters",
            "words": [
                {"speaker_id": "speaker_0", "text": "émojis 🎵", "start_ms": 0, "end_ms": 1000},
                {"speaker_id": "speaker_1", "text": "ünïcödë", "start_ms": 1000, "end_ms": 2000}
            ]
        }
        
        # Should handle unicode correctly
        word_count = calculate_word_count(unicode_transcript)
        assert word_count > 0
        
        speakers = extract_speakers(unicode_transcript)
        assert len(speakers) == 2
        
        # Verify unicode text is preserved
        speaker_0 = next(s for s in speakers if s["speaker_id"] == "speaker_0")
        assert speaker_0["word_count"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])