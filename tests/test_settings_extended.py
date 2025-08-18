"""
Extended tests for settings.py module covering OpenAI API key management and model configuration.

This test suite covers the new OpenAI API key functions and model configuration system.
"""
import pytest
import json
from unittest.mock import patch, mock_open

from app.settings import (
    get_openai_api_key, save_openai_api_key, 
    get_model_config, save_model_config, get_default_model_config
)


class TestOpenAISettings:
    """Test OpenAI API key management functions."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.test_openai_key = "sk-openai123456789abcdef"
        self.test_settings = {
            "elevenlabs_api_key": "sk-eleven123456789abcdef",
            "openai_api_key": self.test_openai_key,
            "other_setting": "test_value"
        }
    
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_openai_api_key_success(self, mock_file, mock_exists):
        """Test successful OpenAI API key retrieval."""
        # Mock file exists and contains valid JSON
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(self.test_settings)
        
        # Get OpenAI API key
        api_key = get_openai_api_key()
        
        # Verify result
        assert api_key == self.test_openai_key
        mock_exists.assert_called_once_with("/app/data/settings.json")
        mock_file.assert_called_once_with("/app/data/settings.json", 'r')
    
    @patch('app.settings.os.path.exists')
    def test_get_openai_api_key_no_file(self, mock_exists):
        """Test OpenAI API key retrieval when file doesn't exist."""
        # Mock file doesn't exist
        mock_exists.return_value = False
        
        # Get OpenAI API key
        api_key = get_openai_api_key()
        
        # Should return None
        assert api_key is None
        mock_exists.assert_called_once_with("/app/data/settings.json")
    
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_openai_api_key_missing_key(self, mock_file, mock_exists):
        """Test OpenAI API key retrieval when key is missing from settings."""
        # Mock file exists but doesn't contain the OpenAI API key
        settings_without_key = {"elevenlabs_api_key": "sk-eleven123", "other_setting": "test_value"}
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(settings_without_key)
        
        # Get OpenAI API key
        api_key = get_openai_api_key()
        
        # Should return None
        assert api_key is None
    
    @patch('app.settings.os.makedirs')
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_openai_api_key_new_file(self, mock_file, mock_exists, mock_makedirs):
        """Test saving OpenAI API key to new file."""
        # Mock file doesn't exist
        mock_exists.return_value = False
        
        # Save OpenAI API key
        save_openai_api_key(self.test_openai_key)
        
        # Verify directory creation
        mock_makedirs.assert_called_once_with("/app/data", exist_ok=True)
        
        # Verify file operations
        mock_file.assert_called_with("/app/data/settings.json", 'w')
        
        # Get the written content
        handle = mock_file()
        written_content = ''.join(call.args[0] for call in handle.write.call_args_list)
        written_settings = json.loads(written_content)
        
        assert written_settings["openai_api_key"] == self.test_openai_key
    
    @patch('app.settings.os.makedirs')
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_openai_api_key_preserve_existing(self, mock_file, mock_exists, mock_makedirs):
        """Test saving OpenAI API key preserves existing settings."""
        # Mock file exists with existing settings
        existing_settings = {
            "elevenlabs_api_key": "sk-eleven123456789abcdef",
            "other_setting": "existing_value"
        }
        mock_exists.return_value = True
        
        # Mock reading existing file
        mock_file.return_value.read.return_value = json.dumps(existing_settings)
        
        # Save OpenAI API key
        save_openai_api_key(self.test_openai_key)
        
        # Verify directory creation still called
        mock_makedirs.assert_called_once_with("/app/data", exist_ok=True)
        
        # Verify file was opened for both read and write
        assert mock_file.call_count >= 2
    
    def test_save_openai_api_key_with_whitespace(self):
        """Test saving OpenAI API key with whitespace (should be stripped)."""
        api_key_with_spaces = f"  {self.test_openai_key}  "
        
        with patch('app.settings.os.makedirs'), \
             patch('app.settings.os.path.exists', return_value=False), \
             patch('builtins.open', mock_open()) as mock_file:
            
            save_openai_api_key(api_key_with_spaces)
            
            # Get the written content
            handle = mock_file()
            written_content = ''.join(call.args[0] for call in handle.write.call_args_list)
            written_settings = json.loads(written_content)
            
            # API key should be stripped
            assert written_settings["openai_api_key"] == self.test_openai_key


class TestModelConfiguration:
    """Test model configuration management functions."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.test_model_config = {
            "models": {
                "embedding": "text-embedding-3-small",
                "entity_extraction": "gpt-5-nano",
                "summarization": "gpt-5-nano",
                "topic_modeling": "gpt-5-nano",
                "question_answering": "gpt-5-mini",
                "knowledge_synthesis": "gpt-5",
                "fallback": "gpt-4o-mini"
            },
            "processing_tiers": {
                "batch": True,
                "use_cache": True,
                "cost_optimization": True
            },
            "limits": {
                "max_tokens_extraction": 1000,
                "max_tokens_qa": 2000,
                "temperature_extraction": 0.1,
                "temperature_qa": 0.7
            }
        }
        
        self.test_settings_with_config = {
            "elevenlabs_api_key": "sk-eleven123",
            "openai_api_key": "sk-openai123",
            "model_config": self.test_model_config
        }
    
    def test_get_default_model_config(self):
        """Test getting default model configuration."""
        config = get_default_model_config()
        
        # Verify structure
        assert "models" in config
        assert "processing_tiers" in config
        assert "limits" in config
        
        # Verify models
        assert config["models"]["embedding"] == "text-embedding-3-small"
        assert config["models"]["entity_extraction"] == "gpt-5-nano"
        assert config["models"]["question_answering"] == "gpt-5-mini"
        assert config["models"]["knowledge_synthesis"] == "gpt-5"
        assert config["models"]["fallback"] == "gpt-4o-mini"
        
        # Verify processing tiers
        assert config["processing_tiers"]["batch"] is True
        assert config["processing_tiers"]["use_cache"] is True
        assert config["processing_tiers"]["cost_optimization"] is True
        
        # Verify limits
        assert config["limits"]["max_tokens_extraction"] == 1000
        assert config["limits"]["max_tokens_qa"] == 2000
        assert config["limits"]["temperature_extraction"] == 0.1
        assert config["limits"]["temperature_qa"] == 0.7
    
    @patch('app.settings.get_settings')
    def test_get_model_config_with_existing_config(self, mock_get_settings):
        """Test getting model configuration when it exists in settings."""
        # Mock settings with model config
        mock_get_settings.return_value = self.test_settings_with_config
        
        config = get_model_config()
        
        # Should return the stored config
        assert config == self.test_model_config
        mock_get_settings.assert_called_once()
    
    @patch('app.settings.get_settings')
    def test_get_model_config_missing_returns_default(self, mock_get_settings):
        """Test getting model configuration returns default when missing."""
        # Mock settings without model config
        mock_get_settings.return_value = {
            "elevenlabs_api_key": "sk-eleven123",
            "openai_api_key": "sk-openai123"
        }
        
        config = get_model_config()
        
        # Should return default config
        default_config = get_default_model_config()
        assert config == default_config
        mock_get_settings.assert_called_once()
    
    @patch('app.settings.os.makedirs')
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_model_config_new_file(self, mock_file, mock_exists, mock_makedirs):
        """Test saving model configuration to new file."""
        # Mock file doesn't exist
        mock_exists.return_value = False
        
        # Save model config
        save_model_config(self.test_model_config)
        
        # Verify directory creation
        mock_makedirs.assert_called_once_with("/app/data", exist_ok=True)
        
        # Verify file operations
        mock_file.assert_called_with("/app/data/settings.json", 'w')
        
        # Get the written content
        handle = mock_file()
        written_content = ''.join(call.args[0] for call in handle.write.call_args_list)
        written_settings = json.loads(written_content)
        
        assert written_settings["model_config"] == self.test_model_config
    
    @patch('app.settings.os.makedirs')
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_model_config_preserve_existing(self, mock_file, mock_exists, mock_makedirs):
        """Test saving model configuration preserves existing settings."""
        # Mock file exists with existing settings
        existing_settings = {
            "elevenlabs_api_key": "sk-eleven123456789abcdef",
            "openai_api_key": "sk-openai123456789abcdef",
            "other_setting": "existing_value"
        }
        mock_exists.return_value = True
        
        # Mock reading existing file
        mock_file.return_value.read.return_value = json.dumps(existing_settings)
        
        # Save model config
        save_model_config(self.test_model_config)
        
        # Verify directory creation still called
        mock_makedirs.assert_called_once_with("/app/data", exist_ok=True)
        
        # Verify file was opened for both read and write
        assert mock_file.call_count >= 2
    
    @patch('app.settings.os.makedirs')
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_model_config_overwrites_existing(self, mock_file, mock_exists, mock_makedirs):
        """Test saving model configuration overwrites existing model config."""
        # Mock file exists with existing model config
        existing_settings = {
            "elevenlabs_api_key": "sk-eleven123",
            "model_config": {
                "models": {"test": "old-model"},
                "old_setting": "should_be_replaced"
            }
        }
        mock_exists.return_value = True
        
        # Mock reading existing file
        mock_file.return_value.read.return_value = json.dumps(existing_settings)
        
        # Save new model config
        save_model_config(self.test_model_config)
        
        # Verify the operation was attempted
        mock_makedirs.assert_called_once_with("/app/data", exist_ok=True)


class TestIntegratedSettings:
    """Test integrated settings functionality with both ElevenLabs and OpenAI keys."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.complete_settings = {
            "elevenlabs_api_key": "sk-eleven123456789abcdef",
            "openai_api_key": "sk-openai123456789abcdef",
            "model_config": {
                "models": {
                    "embedding": "text-embedding-3-small",
                    "entity_extraction": "gpt-5-nano",
                    "summarization": "gpt-5-nano",
                    "question_answering": "gpt-5-mini",
                    "knowledge_synthesis": "gpt-5",
                    "fallback": "gpt-4o-mini"
                },
                "processing_tiers": {
                    "batch": True,
                    "use_cache": True,
                    "cost_optimization": True
                }
            },
            "other_setting": "preserved_value"
        }
    
    @patch('app.settings.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_all_settings_functions_with_complete_config(self, mock_file, mock_exists):
        """Test all settings functions work with complete configuration."""
        # Mock file exists and contains complete settings
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(self.complete_settings)
        
        # Test ElevenLabs API key retrieval
        from app.settings import get_api_key
        elevenlabs_key = get_api_key()
        assert elevenlabs_key == "sk-eleven123456789abcdef"
        
        # Test OpenAI API key retrieval
        openai_key = get_openai_api_key()
        assert openai_key == "sk-openai123456789abcdef"
        
        # Test model configuration retrieval
        model_config = get_model_config()
        assert model_config == self.complete_settings["model_config"]
        
        # Verify file was accessed multiple times
        assert mock_file.call_count >= 3
    
    def test_backward_compatibility_without_openai_key(self):
        """Test that existing functionality works without OpenAI key."""
        settings_without_openai = {
            "elevenlabs_api_key": "sk-eleven123456789abcdef",
            "other_setting": "preserved_value"
        }
        
        with patch('app.settings.os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(settings_without_openai))):
            
            # ElevenLabs key should work
            from app.settings import get_api_key
            elevenlabs_key = get_api_key()
            assert elevenlabs_key == "sk-eleven123456789abcdef"
            
            # OpenAI key should return None gracefully
            openai_key = get_openai_api_key()
            assert openai_key is None
            
            # Model config should return defaults
            model_config = get_model_config()
            default_config = get_default_model_config()
            assert model_config == default_config
    
    def test_backward_compatibility_without_model_config(self):
        """Test that model config returns defaults when not present."""
        settings_without_model_config = {
            "elevenlabs_api_key": "sk-eleven123456789abcdef",
            "openai_api_key": "sk-openai123456789abcdef"
        }
        
        with patch('app.settings.os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(settings_without_model_config))):
            
            # Model config should return defaults
            model_config = get_model_config()
            default_config = get_default_model_config()
            assert model_config == default_config


if __name__ == "__main__":
    pytest.main([__file__, "-v"])