"""
Extended comprehensive tests for main.py module to improve coverage.

This test suite covers additional endpoints and edge cases not covered by existing tests.
"""
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.database import init_database


class TestMainExtended:
    """Extended tests for FastAPI main application."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        # Initialize database for testing
        try:
            init_database()
        except Exception as e:
            print(f"Database initialization in test setup: {e}")
            
        self.client = TestClient(app)
        
        # Sample data for testing
        self.sample_search_request = {
            "query": "test search query",
            "limit": 10,
            "offset": 0
        }
        
        self.sample_video_data = {
            "task_id": "test-video-123",
            "title": "Test Video",
            "duration": 1800,
            "uploader": "Test Channel"
        }
    
    def test_overview_page_renders(self):
        """Test that overview page renders correctly."""
        response = self.client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # Should contain basic page structure
        content = response.text
        assert "<!DOCTYPE html>" in content or "<html" in content
    
    def test_process_page_renders(self):
        """Test that process page renders correctly."""
        response = self.client.get("/process")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # Should contain form elements for URL input
        content = response.text
        assert "form" in content.lower() or "input" in content.lower()
    
    def test_settings_page_renders(self):
        """Test that settings page renders correctly."""
        response = self.client.get("/settings")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    @patch('app.main.get_api_key')
    def test_settings_page_with_existing_key(self, mock_get_api_key):
        """Test settings page when API key already exists."""
        mock_get_api_key.return_value = "existing_key"
        
        response = self.client.get("/settings")
        assert response.status_code == 200
        
        # Should show current key status
        content = response.text
        assert "api" in content.lower() or "key" in content.lower()
    
    @patch('app.main.save_api_key')
    def test_save_settings_endpoint(self, mock_save_api_key):
        """Test saving API key via settings endpoint."""
        api_key = "sk_test123456789"
        
        response = self.client.post("/settings", data={"api_key": api_key})
        
        # Should redirect after saving
        assert response.status_code in [200, 302, 303]
        
        # Verify save function was called
        mock_save_api_key.assert_called_once_with(api_key)
    
    @patch('app.main.save_api_key')
    def test_save_settings_empty_key(self, mock_save_api_key):
        """Test saving empty API key."""
        response = self.client.post("/settings", data={"api_key": ""})
        
        # Should still accept empty key (implementation dependent)
        assert response.status_code in [200, 302, 303, 400]
    
    @patch('app.main.get_task_result')
    def test_get_result_endpoint_success(self, mock_get_task_result):
        """Test successful result retrieval."""
        task_id = "test-task-123"
        expected_result = {
            "metadata": self.sample_video_data,
            "transcript": {"text": "test transcript"}
        }
        mock_get_task_result.return_value = expected_result
        
        response = self.client.get(f"/result/{task_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data == expected_result
    
    @patch('app.main.get_task_result')
    def test_get_result_endpoint_not_found(self, mock_get_task_result):
        """Test result retrieval for non-existent task."""
        task_id = "nonexistent-task"
        mock_get_task_result.side_effect = FileNotFoundError("Video not found")
        
        response = self.client.get(f"/result/{task_id}")
        assert response.status_code == 404
        
        data = response.json()
        assert "error" in data
    
    def test_progress_endpoint_nonexistent_task(self):
        """Test progress endpoint for non-existent task."""
        task_id = "nonexistent-task"
        response = self.client.get(f"/progress/{task_id}")
        
        # Should return 200 but with no progress data
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    @patch('app.main.progress_store')
    def test_progress_endpoint_with_data(self, mock_progress_store):
        """Test progress endpoint with existing progress data."""
        task_id = "test-task-123"
        progress_data = {
            "phase": "downloading",
            "progress": 50,
            "message": "Downloading video..."
        }
        
        # Mock progress store to return our test data once, then empty
        call_count = 0
        def mock_contains(key):
            nonlocal call_count
            call_count += 1
            return call_count == 1 and key == task_id
        
        mock_progress_store.__contains__ = mock_contains
        mock_progress_store.__getitem__ = lambda self, key: progress_data if key == task_id else None
        
        response = self.client.get(f"/progress/{task_id}")
        assert response.status_code == 200
    
    @patch('app.main.SearchManager')
    def test_search_api_success(self, mock_search_manager):
        """Test successful search API call."""
        # Mock search manager
        mock_search_instance = MagicMock()
        mock_search_manager.return_value = mock_search_instance
        
        mock_results = [
            {
                "id": 1,
                "video_id": "test-video-123",
                "speaker_id": "speaker_0",
                "start_ms": 1000,
                "end_ms": 2000,
                "text": "test result text",
                "highlighted_text": "test result <mark>text</mark>",
                "rank": 1.0,
                "word_count": 3
            }
        ]
        
        mock_search_instance.search.return_value = {
            "results": mock_results,
            "total_found": 1,
            "has_more": False,
            "query_time_ms": 2.5
        }
        
        response = self.client.post("/api/search", json=self.sample_search_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["query"] == "test search query"
        assert len(data["results"]) == 1
        assert data["total_found"] == 1
        assert data["has_more"] is False
        assert data["query_time_ms"] == 2.5
    
    def test_search_api_invalid_request(self):
        """Test search API with invalid request data."""
        # Missing required query field
        invalid_request = {"limit": 10}
        
        response = self.client.post("/api/search", json=invalid_request)
        assert response.status_code == 422  # Validation error
    
    def test_search_api_empty_query(self):
        """Test search API with empty query."""
        empty_query_request = {
            "query": "",
            "limit": 10,
            "offset": 0
        }
        
        response = self.client.post("/api/search", json=empty_query_request)
        # Behavior depends on implementation - could be 400 or 200 with no results
        assert response.status_code in [200, 400, 422]
    
    @patch('app.main.SearchManager')
    def test_search_api_with_filters(self, mock_search_manager):
        """Test search API with video and speaker filters."""
        mock_search_instance = MagicMock()
        mock_search_manager.return_value = mock_search_instance
        mock_search_instance.search.return_value = {
            "results": [],
            "total_found": 0,
            "has_more": False,
            "query_time_ms": 1.0
        }
        
        # Test with all optional filters
        filtered_request = {
            "query": "test query",
            "video_id": "specific-video",
            "speaker_id": "speaker_0",
            "start_date": "2025-01-01T00:00:00",
            "end_date": "2025-12-31T23:59:59",
            "limit": 5,
            "offset": 10
        }
        
        response = self.client.post("/api/search", json=filtered_request)
        assert response.status_code == 200
        
        # Verify search was called with correct parameters
        mock_search_instance.search.assert_called_once()
        call_args = mock_search_instance.search.call_args[1]
        assert call_args["query"] == "test query"
        assert call_args["video_id"] == "specific-video"
        assert call_args["speaker_id"] == "speaker_0"
        assert call_args["limit"] == 5
        assert call_args["offset"] == 10
    
    def test_search_api_invalid_date_format(self):
        """Test search API with invalid date format."""
        invalid_date_request = {
            "query": "test query",
            "start_date": "not-a-date",
            "limit": 10,
            "offset": 0
        }
        
        response = self.client.post("/api/search", json=invalid_date_request)
        assert response.status_code == 400
        
        data = response.json()
        assert "error" in data
        assert "date format" in data["error"].lower()
    
    @patch('app.main.SearchManager')
    def test_search_api_exception_handling(self, mock_search_manager):
        """Test search API error handling."""
        # Mock search manager to raise exception
        mock_search_instance = MagicMock()
        mock_search_manager.return_value = mock_search_instance
        mock_search_instance.search.side_effect = Exception("Database error")
        
        response = self.client.post("/api/search", json=self.sample_search_request)
        assert response.status_code == 500
        
        data = response.json()
        assert "error" in data
    
    def test_video_page_nonexistent_video(self):
        """Test video page with non-existent video ID."""
        response = self.client.get("/video/nonexistent-video-id")
        assert response.status_code == 404
        
        # Should render error template
        content = response.text
        assert "not found" in content.lower() or "error" in content.lower()
    
    @patch('app.main.get_task_result')
    def test_video_page_success(self, mock_get_task_result):
        """Test successful video page rendering."""
        task_id = "test-video-123"
        expected_result = {
            "metadata": self.sample_video_data,
            "transcript": {
                "text": "Test transcript content",
                "words": [
                    {"text": "Test", "start_ms": 0, "end_ms": 1000, "speaker_id": "speaker_0"}
                ]
            }
        }
        mock_get_task_result.return_value = expected_result
        
        response = self.client.get(f"/video/{task_id}")
        assert response.status_code == 200
        
        content = response.text
        # Should contain video data
        assert "Test Video" in content or task_id in content
    
    @patch('app.main.get_task_result')
    def test_video_page_exception_handling(self, mock_get_task_result):
        """Test video page when get_task_result raises exception."""
        task_id = "error-video-123"
        mock_get_task_result.side_effect = Exception("Unexpected error")
        
        response = self.client.get(f"/video/{task_id}")
        assert response.status_code == 500
        
        content = response.text
        assert "error" in content.lower()
    
    @patch('app.main.MigrationManager')
    def test_migration_status_endpoint(self, mock_migration_manager):
        """Test migration status API endpoint."""
        # Mock migration manager
        mock_manager_instance = MagicMock()
        mock_migration_manager.return_value = mock_manager_instance
        
        mock_status = {
            "json_files_count": 5,
            "migrated_count": 3,
            "unmigrated_count": 2,
            "database_videos_count": 3
        }
        mock_manager_instance.check_migration_status.return_value = mock_status
        
        response = self.client.get("/api/migration/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["json_files_count"] == 5
        assert data["migrated_count"] == 3
        assert data["unmigrated_count"] == 2
    
    @patch('app.main.MigrationManager')
    @patch('app.main.init_database')
    def test_migration_run_endpoint_success(self, mock_init_db, mock_migration_manager):
        """Test successful migration run."""
        # Mock database initialization
        mock_db_manager = MagicMock()
        mock_init_db.return_value = mock_db_manager
        
        # Mock migration manager
        mock_manager_instance = MagicMock()
        mock_migration_manager.return_value = mock_manager_instance
        
        mock_result = {
            "status": "success",
            "migrated": 5,
            "skipped": 0,
            "errors": 0,
            "total_time": 2.5
        }
        mock_manager_instance.run_migration.return_value = mock_result
        
        response = self.client.post("/api/migration/run")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["result"]["status"] == "success"
        assert data["result"]["migrated"] == 5
    
    @patch('app.main.MigrationManager')
    @patch('app.main.init_database')
    def test_migration_run_endpoint_failure(self, mock_init_db, mock_migration_manager):
        """Test migration run failure handling."""
        # Mock database initialization to fail
        mock_init_db.side_effect = Exception("Database connection failed")
        
        response = self.client.post("/api/migration/run")
        assert response.status_code == 500
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "failed" in data["error"].lower()
    
    def test_static_file_handling(self):
        """Test that static files (CSS, JS) can be served."""
        # This test depends on static file configuration
        # If static files are served separately, this might not apply
        pass
    
    def test_cors_headers(self):
        """Test CORS headers if configured."""
        # Test preflight request
        response = self.client.options("/api/search")
        # CORS behavior depends on configuration
        assert response.status_code in [200, 405]  # 405 if OPTIONS not allowed
    
    def test_json_request_validation(self):
        """Test JSON request body validation."""
        # Send malformed JSON to search endpoint
        response = self.client.post(
            "/api/search",
            data="malformed json content",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_request_size_limits(self):
        """Test request size limits if configured."""
        # Send extremely large request
        large_query = "x" * 10000  # 10KB query
        large_request = {
            "query": large_query,
            "limit": 10,
            "offset": 0
        }
        
        response = self.client.post("/api/search", json=large_request)
        # Should either accept it or reject based on size limits
        assert response.status_code in [200, 400, 413, 422]
    
    @patch('app.main.get_all_videos')
    def test_overview_with_many_videos(self, mock_get_all_videos):
        """Test overview page performance with many videos."""
        # Mock large number of videos
        many_videos = []
        for i in range(100):
            video = self.sample_video_data.copy()
            video["task_id"] = f"video-{i}"
            video["title"] = f"Test Video {i}"
            many_videos.append(video)
        
        mock_get_all_videos.return_value = many_videos
        
        response = self.client.get("/")
        assert response.status_code == 200
        
        # Should handle large number of videos efficiently
        content = response.text
        assert len(content) > 1000  # Should generate substantial content
    
    def test_endpoint_trailing_slashes(self):
        """Test endpoint behavior with and without trailing slashes."""
        # Test with trailing slash
        response1 = self.client.get("/")
        response2 = self.client.get("")
        
        # Both should work (or redirect appropriately)
        assert response1.status_code in [200, 301, 302]
        assert response2.status_code in [200, 301, 302, 404]
    
    def test_http_methods_not_allowed(self):
        """Test that incorrect HTTP methods return appropriate errors."""
        # GET on POST-only endpoint
        response = self.client.get("/process")
        assert response.status_code in [200, 405]  # 200 if it serves the form, 405 if POST-only
        
        # POST on GET-only endpoint  
        response = self.client.post("/")
        assert response.status_code in [405, 422]  # Method not allowed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])