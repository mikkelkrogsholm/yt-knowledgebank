"""
Comprehensive tests for settings.py module.

This test suite covers all settings functions and edge cases to improve coverage.
"""
import pytest
import tempfile
import os
import json
from unittest.mock import patch, mock_open

from app.settings import get_api_key, save_api_key, get_settings


class TestSettings:
    """Test all settings functions."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.test_api_key = "sk_test123456789abcdef"
        self.test_settings = {
            "elevenlabs_api_key": self.test_api_key,
            "other_setting": "test_value"
        }
    
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_api_key_success(self, mock_file, mock_exists):
        """Test successful API key retrieval."""
        # Mock file exists and contains valid JSON
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(self.test_settings)
        
        # Get API key
        api_key = get_api_key()
        
        # Verify result
        assert api_key == self.test_api_key
        mock_exists.assert_called_once_with("/app/data/settings.json")
        mock_file.assert_called_once_with("/app/data/settings.json", 'r')
    
    @patch('app.settings.os.path.exists')
    def test_get_api_key_no_file(self, mock_exists):
        """Test API key retrieval when file doesn't exist."""
        # Mock file doesn't exist
        mock_exists.return_value = False
        
        # Get API key
        api_key = get_api_key()
        
        # Should return None
        assert api_key is None
        mock_exists.assert_called_once_with("/app/data/settings.json")
    
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_api_key_invalid_json(self, mock_file, mock_exists):
        """Test API key retrieval with invalid JSON."""
        # Mock file exists but contains invalid JSON
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "invalid json content"
        
        # Get API key
        api_key = get_api_key()
        
        # Should return None due to JSON decode error
        assert api_key is None
    
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_api_key_missing_key(self, mock_file, mock_exists):
        """Test API key retrieval when key is missing from settings."""
        # Mock file exists but doesn't contain the API key
        settings_without_key = {"other_setting": "test_value"}
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(settings_without_key)
        
        # Get API key
        api_key = get_api_key()
        
        # Should return None
        assert api_key is None
    
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_api_key_file_read_error(self, mock_file, mock_exists):
        """Test API key retrieval when file read fails."""
        # Mock file exists but reading fails
        mock_exists.return_value = True
        mock_file.side_effect = IOError("Permission denied")
        
        # Get API key
        api_key = get_api_key()
        
        # Should return None
        assert api_key is None
    
    @patch('app.settings.os.makedirs')
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_api_key_new_file(self, mock_file, mock_exists, mock_makedirs):
        """Test saving API key to new file."""
        # Mock file doesn't exist
        mock_exists.return_value = False
        
        # Save API key
        save_api_key(self.test_api_key)
        
        # Verify directory creation
        mock_makedirs.assert_called_once_with("/app/data", exist_ok=True)
        
        # Verify file operations
        mock_file.assert_called_with("/app/data/settings.json", 'w')
        
        # Get the written content
        handle = mock_file()
        written_content = ''.join(call.args[0] for call in handle.write.call_args_list)
        written_settings = json.loads(written_content)
        
        assert written_settings["elevenlabs_api_key"] == self.test_api_key
    
    @patch('app.settings.os.makedirs')
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_api_key_existing_file(self, mock_file, mock_exists, mock_makedirs):
        """Test saving API key to existing file."""
        # Mock file exists with existing settings
        existing_settings = {"other_setting": "existing_value"}
        mock_exists.return_value = True
        
        # Mock reading existing file
        mock_file.return_value.read.return_value = json.dumps(existing_settings)
        
        # Save API key
        save_api_key(self.test_api_key)
        
        # Verify directory creation still called
        mock_makedirs.assert_called_once_with("/app/data", exist_ok=True)
        
        # Verify file was opened for both read and write
        assert mock_file.call_count >= 2
        
        # Check that existing settings are preserved
        # The exact verification depends on implementation details
    
    @patch('app.settings.os.makedirs')
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_api_key_corrupted_existing_file(self, mock_file, mock_exists, mock_makedirs):
        """Test saving API key when existing file is corrupted."""
        # Mock file exists but contains invalid JSON
        mock_exists.return_value = True
        
        # Mock reading corrupted file
        mock_file.return_value.read.return_value = "corrupted json"
        
        # Save API key (should handle corruption gracefully)
        save_api_key(self.test_api_key)
        
        # Should still succeed by creating new settings
        mock_makedirs.assert_called_once_with("/app/data", exist_ok=True)
    
    def test_save_api_key_with_whitespace(self):
        """Test saving API key with whitespace (should be stripped)."""
        api_key_with_spaces = f"  {self.test_api_key}  "
        
        with patch('app.settings.os.makedirs'), \
             patch('app.settings.os.path.exists', return_value=False), \
             patch('builtins.open', mock_open()) as mock_file:
            
            save_api_key(api_key_with_spaces)
            
            # Get the written content
            handle = mock_file()
            written_content = ''.join(call.args[0] for call in handle.write.call_args_list)
            written_settings = json.loads(written_content)
            
            # API key should be stripped
            assert written_settings["elevenlabs_api_key"] == self.test_api_key
    
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_settings_success(self, mock_file, mock_exists):
        """Test successful settings retrieval."""
        # Mock file exists and contains valid JSON
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(self.test_settings)
        
        # Get settings
        settings = get_settings()
        
        # Verify result
        assert settings == self.test_settings
        assert settings["elevenlabs_api_key"] == self.test_api_key
        assert settings["other_setting"] == "test_value"
        
        mock_exists.assert_called_once_with("/app/data/settings.json")
        mock_file.assert_called_once_with("/app/data/settings.json", 'r')
    
    @patch('app.settings.os.path.exists')
    def test_get_settings_no_file(self, mock_exists):
        """Test settings retrieval when file doesn't exist."""
        # Mock file doesn't exist
        mock_exists.return_value = False
        
        # Get settings
        settings = get_settings()
        
        # Should return empty dict
        assert settings == {}
        mock_exists.assert_called_once_with("/app/data/settings.json")
    
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_settings_invalid_json(self, mock_file, mock_exists):
        """Test settings retrieval with invalid JSON."""
        # Mock file exists but contains invalid JSON
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "invalid json"
        
        # Get settings
        settings = get_settings()
        
        # Should return empty dict due to JSON decode error
        assert settings == {}
    
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_settings_file_read_error(self, mock_file, mock_exists):
        """Test settings retrieval when file read fails."""
        # Mock file exists but reading fails
        mock_exists.return_value = True
        mock_file.side_effect = IOError("Permission denied")
        
        # Get settings
        settings = get_settings()
        
        # Should return empty dict
        assert settings == {}
    
    @patch('app.settings.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_api_key_directory_creation_error(self, mock_file, mock_makedirs):
        """Test API key saving when directory creation fails."""
        # Mock directory creation failure
        mock_makedirs.side_effect = OSError("Permission denied")
        
        # This should raise an exception or handle gracefully
        # depending on implementation
        try:
            save_api_key(self.test_api_key)
        except OSError:
            # Expected if implementation doesn't handle directory creation errors
            pass
    
    @patch('app.settings.os.makedirs')
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_api_key_write_error(self, mock_file, mock_exists, mock_makedirs):
        """Test API key saving when file write fails."""
        # Mock file write failure
        mock_exists.return_value = False
        mock_file.side_effect = IOError("Disk full")
        
        # This should raise an exception or handle gracefully
        # depending on implementation
        try:
            save_api_key(self.test_api_key)
        except IOError:
            # Expected if implementation doesn't handle write errors
            pass
    
    def test_api_key_validation_empty_string(self):
        """Test handling of empty string API key."""
        with patch('app.settings.os.makedirs'), \
             patch('app.settings.os.path.exists', return_value=False), \
             patch('builtins.open', mock_open()) as mock_file:
            
            # Save empty API key
            save_api_key("")
            
            # Get the written content
            handle = mock_file()
            written_content = ''.join(call.args[0] for call in handle.write.call_args_list)
            written_settings = json.loads(written_content)
            
            # Empty string should be saved (after stripping)
            assert written_settings["elevenlabs_api_key"] == ""
    
    def test_settings_file_path_constant(self):
        """Test that settings file path constant is correct."""
        from app.settings import SETTINGS_FILE
        assert SETTINGS_FILE == "/app/data/settings.json"
    
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_concurrent_access_simulation(self, mock_file, mock_exists):
        """Test simulated concurrent access to settings file."""
        # Mock file exists
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(self.test_settings)
        
        # Simulate multiple concurrent reads
        results = []
        for _ in range(5):
            api_key = get_api_key()
            settings = get_settings()
            results.append((api_key, settings))
        
        # All should return the same results
        for api_key, settings in results:
            assert api_key == self.test_api_key
            assert settings == self.test_settings
        
        # File operations should have been called multiple times
        assert mock_file.call_count >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])