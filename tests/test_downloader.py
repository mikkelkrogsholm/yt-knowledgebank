"""
Comprehensive tests for downloader.py module.

This test suite covers all download functions and edge cases to improve coverage.
"""
import pytest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock, mock_open, call

from app.downloader import process_youtube_url, progress_store


class TestDownloader:
    """Test all downloader functions."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.test_url = "https://youtu.be/test123"
        self.test_task_id = "test-task-123"
        
        # Sample yt-dlp info response
        self.sample_info = {
            "id": "test123",
            "title": "Test Video: Amazing Content",
            "duration": 1800,
            "uploader": "Test Channel",
            "view_count": 50000,
            "upload_date": "20250817",
            "webpage_url": self.test_url,
            "thumbnail": "https://example.com/thumb.jpg",
            "description": "Test video description"
        }
    
    @patch('app.downloader.yt_dlp.YoutubeDL')
    def test_extract_metadata_success(self, mock_youtubedl):
        """Test successful metadata extraction."""
        # Mock yt-dlp
        mock_ydl_instance = MagicMock()
        mock_youtubedl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = self.sample_info
        
        # Extract metadata
        metadata = extract_metadata(self.test_url)
        
        # Verify results
        assert metadata is not None
        assert metadata["id"] == "test123"
        assert metadata["title"] == "Test Video: Amazing Content"
        assert metadata["duration"] == 1800
        assert metadata["uploader"] == "Test Channel"
        assert metadata["view_count"] == 50000
        assert metadata["upload_date"] == "20250817"
        assert metadata["webpage_url"] == self.test_url
        
        # Verify yt-dlp was called correctly
        mock_ydl_instance.extract_info.assert_called_once_with(self.test_url, download=False)
    
    @patch('app.downloader.yt_dlp.YoutubeDL')
    def test_extract_metadata_failure(self, mock_youtubedl):
        """Test metadata extraction failure."""
        # Mock yt-dlp to raise exception
        mock_ydl_instance = MagicMock()
        mock_youtubedl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.side_effect = Exception("Video not available")
        
        # Extract metadata should return None on failure
        metadata = extract_metadata(self.test_url)
        assert metadata is None
    
    @patch('app.downloader.yt_dlp.YoutubeDL')
    def test_extract_metadata_invalid_url(self, mock_youtubedl):
        """Test metadata extraction with invalid URL."""
        # Mock yt-dlp to raise exception for invalid URL
        mock_ydl_instance = MagicMock()
        mock_youtubedl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.side_effect = Exception("Invalid URL")
        
        # Should handle gracefully
        metadata = extract_metadata("not-a-valid-url")
        assert metadata is None
    
    @patch('app.downloader.yt_dlp.YoutubeDL')
    @patch('app.downloader.os.makedirs')
    def test_download_audio_success(self, mock_makedirs, mock_youtubedl):
        """Test successful audio download."""
        # Mock yt-dlp
        mock_ydl_instance = MagicMock()
        mock_youtubedl.return_value.__enter__.return_value = mock_ydl_instance
        
        # Mock successful download
        mock_ydl_instance.download.return_value = None  # Success case
        
        # Test download
        result = download_audio(self.test_url, self.test_task_id)
        
        # Verify success
        assert result is True
        
        # Verify directory creation
        expected_dir = f"/app/data/videos/{self.test_task_id}"
        mock_makedirs.assert_called_once_with(expected_dir, exist_ok=True)
        
        # Verify yt-dlp was called correctly
        mock_ydl_instance.download.assert_called_once_with([self.test_url])
    
    @patch('app.downloader.yt_dlp.YoutubeDL')
    @patch('app.downloader.os.makedirs')
    def test_download_audio_failure(self, mock_makedirs, mock_youtubedl):
        """Test audio download failure."""
        # Mock yt-dlp to raise exception
        mock_ydl_instance = MagicMock()
        mock_youtubedl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.download.side_effect = Exception("Download failed")
        
        # Test download
        result = download_audio(self.test_url, self.test_task_id)
        
        # Verify failure
        assert result is False
        
        # Directory creation should still be attempted
        expected_dir = f"/app/data/videos/{self.test_task_id}"
        mock_makedirs.assert_called_once_with(expected_dir, exist_ok=True)
    
    @patch('app.downloader.yt_dlp.YoutubeDL')
    @patch('app.downloader.os.makedirs')
    def test_download_audio_directory_creation_failure(self, mock_makedirs, mock_youtubedl):
        """Test download when directory creation fails."""
        # Mock directory creation to fail
        mock_makedirs.side_effect = OSError("Permission denied")
        
        # Mock yt-dlp (should not be called due to directory failure)
        mock_ydl_instance = MagicMock()
        mock_youtubedl.return_value.__enter__.return_value = mock_ydl_instance
        
        # Test download
        result = download_audio(self.test_url, self.test_task_id)
        
        # Should fail due to directory creation failure
        assert result is False
        
        # yt-dlp should not be called
        mock_ydl_instance.download.assert_not_called()
    
    @patch('app.downloader.yt_dlp.YoutubeDL')
    def test_extract_metadata_missing_fields(self, mock_youtubedl):
        """Test metadata extraction when some fields are missing."""
        # Mock yt-dlp with incomplete info
        incomplete_info = {
            "id": "test123",
            "title": "Test Video",
            # Missing duration, uploader, etc.
        }
        
        mock_ydl_instance = MagicMock()
        mock_youtubedl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = incomplete_info
        
        # Extract metadata
        metadata = extract_metadata(self.test_url)
        
        # Should still return what's available
        assert metadata is not None
        assert metadata["id"] == "test123"
        assert metadata["title"] == "Test Video"
        # Missing fields should be handled by the calling code
    
    @patch('app.downloader.yt_dlp.YoutubeDL')
    def test_extract_metadata_special_characters(self, mock_youtubedl):
        """Test metadata extraction with special characters in title."""
        # Mock yt-dlp with special characters
        special_info = self.sample_info.copy()
        special_info["title"] = "Test Video: Special Chars & Unicode 🎵"
        
        mock_ydl_instance = MagicMock()
        mock_youtubedl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = special_info
        
        # Extract metadata
        metadata = extract_metadata(self.test_url)
        
        # Should handle special characters correctly
        assert metadata is not None
        assert metadata["title"] == "Test Video: Special Chars & Unicode 🎵"
    
    @patch('app.downloader.yt_dlp.YoutubeDL')
    @patch('app.downloader.os.makedirs')
    def test_download_audio_custom_path(self, mock_makedirs, mock_youtubedl):
        """Test download with custom task ID path."""
        custom_task_id = "custom-task-with-hyphens-123"
        
        # Mock yt-dlp
        mock_ydl_instance = MagicMock()
        mock_youtubedl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.download.return_value = None
        
        # Test download
        result = download_audio(self.test_url, custom_task_id)
        
        # Verify success
        assert result is True
        
        # Verify correct directory path
        expected_dir = f"/app/data/videos/{custom_task_id}"
        mock_makedirs.assert_called_once_with(expected_dir, exist_ok=True)
    
    @patch('app.downloader.yt_dlp.YoutubeDL')
    def test_youtubedl_options_configuration(self, mock_youtubedl):
        """Test that YoutubeDL is configured with correct options."""
        mock_ydl_instance = MagicMock()
        mock_youtubedl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = self.sample_info
        
        # Call extract_metadata to trigger YoutubeDL creation
        extract_metadata(self.test_url)
        
        # Verify YoutubeDL was created (options are checked in actual implementation)
        mock_youtubedl.assert_called_once()
        call_args = mock_youtubedl.call_args[0][0]  # First argument (options dict)
        
        # Verify key options are set
        assert 'format' in call_args
        assert call_args['quiet'] is True
        assert call_args['no_warnings'] is True
    
    @patch('app.downloader.yt_dlp.YoutubeDL')
    @patch('app.downloader.os.makedirs')
    def test_download_audio_options_configuration(self, mock_makedirs, mock_youtubedl):
        """Test that audio download is configured with correct options."""
        mock_ydl_instance = MagicMock()
        mock_youtubedl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.download.return_value = None
        
        # Call download_audio to trigger YoutubeDL creation
        download_audio(self.test_url, self.test_task_id)
        
        # Verify YoutubeDL was created with audio-specific options
        mock_youtubedl.assert_called_once()
        call_args = mock_youtubedl.call_args[0][0]  # First argument (options dict)
        
        # Verify audio download options
        assert 'format' in call_args
        assert 'outtmpl' in call_args
        assert self.test_task_id in call_args['outtmpl']
        assert call_args['quiet'] is True
    
    def test_edge_case_empty_url(self):
        """Test handling of empty URL."""
        # Should handle empty URL gracefully
        metadata = extract_metadata("")
        assert metadata is None
        
        result = download_audio("", self.test_task_id)
        assert result is False
    
    def test_edge_case_none_url(self):
        """Test handling of None URL."""
        # Should handle None URL gracefully
        metadata = extract_metadata(None)
        assert metadata is None
        
        result = download_audio(None, self.test_task_id)
        assert result is False
    
    @patch('app.downloader.yt_dlp.YoutubeDL')
    def test_multiple_extractions(self, mock_youtubedl):
        """Test multiple metadata extractions in sequence."""
        mock_ydl_instance = MagicMock()
        mock_youtubedl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = self.sample_info
        
        # Extract metadata multiple times
        urls = [
            "https://youtu.be/test1",
            "https://youtu.be/test2",
            "https://youtu.be/test3"
        ]
        
        results = []
        for url in urls:
            result = extract_metadata(url)
            results.append(result)
        
        # All should succeed
        assert all(r is not None for r in results)
        assert len(results) == 3
        
        # Should have been called for each URL
        assert mock_ydl_instance.extract_info.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])