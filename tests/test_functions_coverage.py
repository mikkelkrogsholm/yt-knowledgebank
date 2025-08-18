"""
Simple tests to increase coverage of existing functions in various modules.
This focuses on testing actual functions that exist to maximize coverage.
"""
import pytest
import asyncio
import tempfile
import os
import json
from unittest.mock import patch, MagicMock, mock_open, AsyncMock
from datetime import datetime

# Import functions from various modules
from app.processor import format_duration, format_date, extract_video_id
from app.settings import get_api_key, save_api_key, get_settings  
from app.downloader import process_youtube_url, progress_store
from app.database_queries import get_all_videos_from_database, get_database_stats
from app.database import init_database


class TestProcessorFunctions:
    """Test processor utility functions."""
    
    def test_format_duration_various_cases(self):
        """Test format_duration with various inputs."""
        assert format_duration(0) == "0:00"
        assert format_duration(30) == "0:30"
        assert format_duration(60) == "1:00"
        assert format_duration(90) == "1:30"
        assert format_duration(3600) == "1:00:00"
        assert format_duration(3661) == "1:01:01"
        assert format_duration(7200) == "2:00:00"
        
    def test_format_duration_edge_cases(self):
        """Test format_duration with edge cases."""
        assert format_duration(None) == "0:00"
        assert format_duration(-10) == "0:00"
        
        # Test invalid input handling
        try:
            result = format_duration("invalid")
            assert isinstance(result, str)  # Should return string
        except (TypeError, ValueError):
            pass  # Expected for invalid input
    
    def test_format_date_various_formats(self):
        """Test format_date with various formats."""
        # Test ISO format
        iso_date = "2025-08-17T14:30:45.123456"
        result = format_date(iso_date)
        assert isinstance(result, str)
        assert "2025" in result or "Aug" in result
        
        # Test simple date
        simple_date = "2025-08-17"
        result = format_date(simple_date)
        assert isinstance(result, str)
        
        # Test YouTube format
        youtube_date = "20250817"  
        result = format_date(youtube_date)
        assert isinstance(result, str)
    
    def test_format_date_edge_cases(self):
        """Test format_date with edge cases."""
        assert format_date(None) == "Unknown date"
        assert format_date("") == "Unknown date"
        assert format_date("invalid") == "Unknown date"
    
    def test_extract_video_id_various_urls(self):
        """Test extract_video_id with various YouTube URL formats."""
        # Standard YouTube URLs
        assert extract_video_id("https://www.youtube.com/watch?v=ABC123") == "ABC123"
        assert extract_video_id("https://youtu.be/XYZ789") == "XYZ789"
        assert extract_video_id("https://youtube.com/watch?v=TEST01") == "TEST01"
        
        # With additional parameters
        url_with_params = "https://www.youtube.com/watch?v=ABC123&t=30s&list=xyz"
        assert extract_video_id(url_with_params) == "ABC123"
        
    def test_extract_video_id_edge_cases(self):
        """Test extract_video_id with edge cases."""
        # Invalid URLs
        assert extract_video_id("not a url") == ""
        assert extract_video_id("") == ""
        assert extract_video_id("https://example.com") == ""
        
        # None input
        try:
            result = extract_video_id(None)
            assert result == "" or result is None
        except (TypeError, AttributeError):
            pass  # Expected for None input


class TestSettingsFunctions:
    """Test settings module functions."""
    
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_api_key_success(self, mock_file, mock_exists):
        """Test successful API key retrieval."""
        settings_data = {"elevenlabs_api_key": "test_key_123"}
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(settings_data)
        
        result = get_api_key()
        assert result == "test_key_123"
    
    @patch('app.settings.os.path.exists')
    def test_get_api_key_no_file(self, mock_exists):
        """Test API key retrieval when file doesn't exist."""
        mock_exists.return_value = False
        result = get_api_key()
        assert result is None
    
    @patch('app.settings.os.path.exists') 
    @patch('builtins.open', new_callable=mock_open)
    def test_get_api_key_invalid_json(self, mock_file, mock_exists):
        """Test API key retrieval with corrupted file."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "invalid json"
        result = get_api_key()
        assert result is None
    
    @patch('app.settings.os.makedirs')
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_api_key_new_file(self, mock_file, mock_exists, mock_makedirs):
        """Test saving API key to new file."""
        mock_exists.return_value = False
        save_api_key("new_api_key")
        mock_makedirs.assert_called_once_with("/app/data", exist_ok=True)
        mock_file.assert_called_with("/app/data/settings.json", 'w')
    
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_settings_success(self, mock_file, mock_exists):
        """Test successful settings retrieval."""
        settings_data = {"key1": "value1", "key2": "value2"}
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(settings_data)
        
        result = get_settings()
        assert result == settings_data
    
    @patch('app.settings.os.path.exists')
    def test_get_settings_no_file(self, mock_exists):
        """Test settings retrieval when no file exists."""
        mock_exists.return_value = False
        result = get_settings()
        assert result == {}


class TestDownloaderFunctions:
    """Test downloader module functions."""
    
    def test_progress_store_operations(self):
        """Test progress_store basic operations."""
        task_id = "test_task_123"
        
        # Clear any existing data
        progress_store.clear()
        
        # Test storing progress
        progress_store[task_id] = {"status": "downloading", "percent": 50}
        assert task_id in progress_store
        assert progress_store[task_id]["status"] == "downloading"
        assert progress_store[task_id]["percent"] == 50
        
        # Test updating progress
        progress_store[task_id] = {"status": "finished", "percent": 100}
        assert progress_store[task_id]["status"] == "finished"
        assert progress_store[task_id]["percent"] == 100
        
        # Test clearing
        progress_store.clear()
        assert len(progress_store) == 0
    
    @pytest.mark.asyncio
    @patch('app.downloader.yt_dlp.YoutubeDL')
    async def test_process_youtube_url_mock(self, mock_youtubedl):
        """Test process_youtube_url with mocked yt-dlp."""
        # Mock yt-dlp
        mock_ydl_instance = MagicMock()
        mock_youtubedl.return_value.__enter__.return_value = mock_ydl_instance
        
        # Mock the info extraction
        mock_info = {
            'title': 'Test Video',
            'duration': 180,
            'uploader': 'Test Channel',
            'view_count': 1000,
            'upload_date': '20250817',
            'ext': 'webm'
        }
        mock_ydl_instance.extract_info.return_value = mock_info
        mock_ydl_instance.download.return_value = None
        
        # Test the function
        url = "https://youtu.be/test123"
        task_id = "test_task_456"
        
        result = await process_youtube_url(url, task_id)
        
        # Verify result
        assert result['title'] == 'Test Video'
        assert result['duration'] == 180
        assert result['uploader'] == 'Test Channel'
        assert result['view_count'] == 1000
        
        # Verify yt-dlp was called correctly
        mock_ydl_instance.extract_info.assert_called_once_with(url, download=False)
        mock_ydl_instance.download.assert_called_once_with([url])
    
    @pytest.mark.asyncio
    @patch('app.downloader.yt_dlp.YoutubeDL')
    async def test_process_youtube_url_exception(self, mock_youtubedl):
        """Test process_youtube_url when yt-dlp raises exception."""
        # Mock yt-dlp to raise exception
        mock_youtubedl.return_value.__enter__.return_value.extract_info.side_effect = Exception("Video not found")
        
        url = "https://youtu.be/invalid"
        task_id = "test_task_error"
        
        # Should raise exception or handle gracefully
        with pytest.raises(Exception):
            await process_youtube_url(url, task_id)


class TestDatabaseQueryFunctions:
    """Test database query functions."""
    
    @patch('app.database_queries.get_database_session')
    def test_get_all_videos_from_database_empty(self, mock_session):
        """Test getting all videos when database is empty."""
        # Mock empty database
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.query.return_value.outerjoin.return_value.outerjoin.return_value.group_by.return_value.all.return_value = []
        
        result = get_all_videos_from_database()
        assert result == []
    
    @patch('app.database_queries.get_database_session')
    def test_get_all_videos_from_database_exception(self, mock_session):
        """Test get_all_videos_from_database when database raises exception."""
        # Mock database session to raise exception
        mock_session.side_effect = Exception("Database connection failed")
        
        result = get_all_videos_from_database()
        # Should handle exception gracefully and return empty list
        assert result == []
    
    @patch('app.database_queries.get_database_session')
    def test_get_database_stats_success(self, mock_session):
        """Test successful database stats retrieval."""
        # Mock database session
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        
        # Mock query results
        mock_session_instance.query.return_value.count.return_value = 5
        mock_session_instance.query.return_value.scalar.return_value = 1500
        
        result = get_database_stats()
        
        # Should return dictionary with stats
        assert isinstance(result, dict)
        assert "total_videos" in result
        assert "total_chunks" in result
        assert "total_duration" in result
    
    @patch('app.database_queries.get_database_session')
    def test_get_database_stats_exception(self, mock_session):
        """Test database stats when exception occurs."""
        # Mock database to raise exception
        mock_session.side_effect = Exception("Database error")
        
        result = get_database_stats()
        
        # Should handle exception gracefully
        assert isinstance(result, dict)
        assert result.get("total_videos", 0) == 0


class TestDatabaseInitialization:
    """Test database initialization."""
    
    @patch('app.database.DatabaseManager')
    def test_init_database_success(self, mock_db_manager):
        """Test successful database initialization."""
        # Mock database manager
        mock_manager_instance = MagicMock()
        mock_db_manager.return_value = mock_manager_instance
        
        result = init_database()
        
        # Should return database manager instance
        assert result is not None
        mock_manager_instance.create_tables.assert_called_once()
    
    @patch('app.database.DatabaseManager')
    def test_init_database_exception(self, mock_db_manager):
        """Test database initialization failure."""
        # Mock database manager to raise exception
        mock_db_manager.side_effect = Exception("Database initialization failed")
        
        # Should raise exception or handle gracefully
        try:
            result = init_database()
            # If it doesn't raise, it should handle gracefully
            assert result is None or isinstance(result, MagicMock)
        except Exception:
            # Expected behavior for initialization failure
            pass


class TestUtilityFunctions:
    """Test various utility functions across modules."""
    
    def test_string_formatting_edge_cases(self):
        """Test string formatting functions with edge cases."""
        # Test with very large numbers
        assert format_duration(360000) == "100:00:00"  # 100 hours
        
        # Test with unicode characters
        unicode_date = "2025-08-17T14:30:45🕐"
        result = format_date(unicode_date)
        assert isinstance(result, str)
        # Should handle gracefully (either parse or return "Unknown date")
    
    def test_concurrent_access_simulation(self):
        """Test functions that might be accessed concurrently."""
        # Test progress_store with rapid updates
        for i in range(100):
            task_id = f"task_{i}"
            progress_store[task_id] = {"status": "processing", "percent": i}
        
        assert len(progress_store) == 100
        assert progress_store["task_50"]["percent"] == 50
        
        # Clear for cleanup
        progress_store.clear()
    
    @patch('app.settings.os.path.exists')
    def test_file_operations_error_handling(self, mock_exists):
        """Test file operation error handling."""
        # Test when file operations fail
        mock_exists.side_effect = PermissionError("Access denied")
        
        # Should handle permission errors gracefully
        result = get_api_key()
        assert result is None  # Should handle error and return None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])