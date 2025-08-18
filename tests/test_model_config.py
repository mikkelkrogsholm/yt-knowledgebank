"""
Tests for model_config.py module.

This test suite covers the ModelConfig class and all its functionality.
"""
import pytest
from unittest.mock import patch

from app.model_config import ModelConfig, get_default_config, create_config_from_dict


class TestModelConfig:
    """Test ModelConfig class functionality."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.test_config = {
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
    
    def test_model_config_initialization_with_config(self):
        """Test ModelConfig initialization with provided config."""
        config = ModelConfig(self.test_config)
        assert config.config == self.test_config
    
    @patch('app.model_config.get_model_config')
    def test_model_config_initialization_without_config(self, mock_get_model_config):
        """Test ModelConfig initialization without provided config."""
        mock_get_model_config.return_value = self.test_config
        
        config = ModelConfig()
        
        assert config.config == self.test_config
        mock_get_model_config.assert_called_once()
    
    def test_get_model_for_task(self):
        """Test getting model for specific task."""
        config = ModelConfig(self.test_config)
        
        assert config.get_model_for_task('embedding') == 'text-embedding-3-small'
        assert config.get_model_for_task('entity_extraction') == 'gpt-5-nano'
        assert config.get_model_for_task('question_answering') == 'gpt-5-mini'
        assert config.get_model_for_task('knowledge_synthesis') == 'gpt-5'
        
        # Test fallback for unknown task
        assert config.get_model_for_task('unknown_task') == 'gpt-4o-mini'
    
    def test_get_model_for_task_missing_fallback(self):
        """Test getting model for task when fallback is missing."""
        config_without_fallback = {
            "models": {
                "embedding": "text-embedding-3-small"
            }
        }
        config = ModelConfig(config_without_fallback)
        
        # Should return 'gpt-4o-mini' as hardcoded fallback
        assert config.get_model_for_task('unknown_task') == 'gpt-4o-mini'
    
    def test_specific_model_getters(self):
        """Test specific model getter methods."""
        config = ModelConfig(self.test_config)
        
        assert config.get_embedding_model() == 'text-embedding-3-small'
        assert config.get_extraction_model() == 'gpt-5-nano'
        assert config.get_summarization_model() == 'gpt-5-nano'
        assert config.get_topic_modeling_model() == 'gpt-5-nano'
        assert config.get_qa_model() == 'gpt-5-mini'
        assert config.get_synthesis_model() == 'gpt-5'
    
    def test_processing_tier_checks(self):
        """Test processing tier configuration checks."""
        config = ModelConfig(self.test_config)
        
        assert config.should_use_batch_processing() is True
        assert config.should_use_cache() is True
        assert config.should_optimize_costs() is True
        
        # Test with missing processing_tiers
        config_without_tiers = {"models": {}}
        config = ModelConfig(config_without_tiers)
        
        assert config.should_use_batch_processing() is True  # Default
        assert config.should_use_cache() is True  # Default
        assert config.should_optimize_costs() is True  # Default
    
    def test_processing_tier_checks_disabled(self):
        """Test processing tier configuration when disabled."""
        config_disabled = {
            "processing_tiers": {
                "batch": False,
                "use_cache": False,
                "cost_optimization": False
            }
        }
        config = ModelConfig(config_disabled)
        
        assert config.should_use_batch_processing() is False
        assert config.should_use_cache() is False
        assert config.should_optimize_costs() is False
    
    def test_get_max_tokens_for_task(self):
        """Test getting maximum tokens for specific tasks."""
        config = ModelConfig(self.test_config)
        
        # Extraction tasks should use extraction limit
        assert config.get_max_tokens_for_task('entity_extraction') == 1000
        assert config.get_max_tokens_for_task('summarization') == 1000
        assert config.get_max_tokens_for_task('topic_modeling') == 1000
        
        # QA tasks should use QA limit
        assert config.get_max_tokens_for_task('question_answering') == 2000
        assert config.get_max_tokens_for_task('knowledge_synthesis') == 2000
        
        # Unknown tasks should use extraction default
        assert config.get_max_tokens_for_task('unknown_task') == 1000
    
    def test_get_temperature_for_task(self):
        """Test getting temperature for specific tasks."""
        config = ModelConfig(self.test_config)
        
        # Extraction tasks should use extraction temperature
        assert config.get_temperature_for_task('entity_extraction') == 0.1
        assert config.get_temperature_for_task('summarization') == 0.1
        assert config.get_temperature_for_task('topic_modeling') == 0.1
        
        # QA tasks should use QA temperature
        assert config.get_temperature_for_task('question_answering') == 0.7
        assert config.get_temperature_for_task('knowledge_synthesis') == 0.7
        
        # Unknown tasks should use extraction default
        assert config.get_temperature_for_task('unknown_task') == 0.1
    
    def test_get_task_config(self):
        """Test getting complete configuration for a task."""
        config = ModelConfig(self.test_config)
        
        extraction_config = config.get_task_config('entity_extraction')
        
        assert extraction_config['model'] == 'gpt-5-nano'
        assert extraction_config['max_tokens'] == 1000
        assert extraction_config['temperature'] == 0.1
        assert extraction_config['use_batch'] is True
        assert extraction_config['use_cache'] is True
        
        qa_config = config.get_task_config('question_answering')
        
        assert qa_config['model'] == 'gpt-5-mini'
        assert qa_config['max_tokens'] == 2000
        assert qa_config['temperature'] == 0.7
        assert qa_config['use_batch'] is True
        assert qa_config['use_cache'] is True
    
    def test_estimate_cost(self):
        """Test cost estimation for different models."""
        config = ModelConfig(self.test_config)
        
        # Test GPT-5 nano cost estimation
        nano_cost = config.estimate_cost('entity_extraction', 1000, 500)
        assert nano_cost['model'] == 'gpt-5-nano'
        assert nano_cost['input_cost'] == (1000 / 1_000_000) * 2.0  # $2 per 1M tokens
        assert nano_cost['output_cost'] == (500 / 1_000_000) * 8.0  # $8 per 1M tokens
        assert nano_cost['total_cost'] == nano_cost['input_cost'] + nano_cost['output_cost']
        
        # Test GPT-5 mini cost estimation
        mini_cost = config.estimate_cost('question_answering', 1000, 500)
        assert mini_cost['model'] == 'gpt-5-mini'
        assert mini_cost['input_cost'] == (1000 / 1_000_000) * 3.0  # $3 per 1M tokens
        assert mini_cost['output_cost'] == (500 / 1_000_000) * 12.0  # $12 per 1M tokens
        
        # Test fallback model cost estimation
        fallback_cost = config.estimate_cost('unknown_task', 1000, 500)
        assert fallback_cost['model'] == 'gpt-4o-mini'
        assert fallback_cost['input_cost'] == (1000 / 1_000_000) * 0.15  # $0.15 per 1M tokens
    
    def test_get_cost_optimized_model(self):
        """Test cost-optimized model selection."""
        config = ModelConfig(self.test_config)
        
        # Small tasks should use nano models
        small_model = config.get_cost_optimized_model('entity_extraction', 400)
        assert small_model == 'gpt-5-nano'
        
        # Medium tasks should use appropriate models
        medium_model = config.get_cost_optimized_model('question_answering', 1500)
        assert medium_model == 'gpt-5-mini'
        
        # Large synthesis tasks should use full models
        large_model = config.get_cost_optimized_model('knowledge_synthesis', 3000)
        assert large_model == 'gpt-5'
        
        # When cost optimization is disabled, use configured model
        config_no_optimization = {
            "models": {"entity_extraction": "gpt-5"},
            "processing_tiers": {"cost_optimization": False}
        }
        config = ModelConfig(config_no_optimization)
        
        no_opt_model = config.get_cost_optimized_model('entity_extraction', 400)
        assert no_opt_model == 'gpt-5'  # Uses configured model, not optimized
    
    def test_validate_config_valid(self):
        """Test configuration validation with valid config."""
        config = ModelConfig(self.test_config)
        
        validation = config.validate_config()
        
        assert validation['valid'] is True
        assert len(validation['issues']) == 0
        assert len(validation['warnings']) == 0
    
    def test_validate_config_missing_models(self):
        """Test configuration validation with missing models."""
        incomplete_config = {
            "models": {
                "embedding": "text-embedding-3-small",
                "entity_extraction": "gpt-5-nano"
                # Missing required models
            }
        }
        config = ModelConfig(incomplete_config)
        
        validation = config.validate_config()
        
        assert validation['valid'] is False
        assert len(validation['issues']) > 0
        
        # Check that missing models are reported
        issues_text = " ".join(validation['issues'])
        assert "summarization" in issues_text
        assert "question_answering" in issues_text
        assert "fallback" in issues_text
    
    def test_validate_config_deprecated_models(self):
        """Test configuration validation with deprecated models."""
        deprecated_config = {
            "models": {
                "embedding": "text-embedding-3-small",
                "entity_extraction": "gpt-4",  # Deprecated
                "summarization": "gpt-3.5-turbo",  # Deprecated
                "topic_modeling": "gpt-5-nano",
                "question_answering": "gpt-5-mini",
                "knowledge_synthesis": "gpt-5",
                "fallback": "gpt-4o-mini"
            }
        }
        config = ModelConfig(deprecated_config)
        
        validation = config.validate_config()
        
        assert validation['valid'] is True  # Still valid, just warnings
        assert len(validation['warnings']) > 0
        
        # Check that deprecated models are warned about
        warnings_text = " ".join(validation['warnings'])
        assert "gpt-4" in warnings_text
        assert "gpt-3.5-turbo" in warnings_text
    
    def test_validate_config_high_token_limits(self):
        """Test configuration validation with high token limits."""
        high_limit_config = {
            "models": {
                "embedding": "text-embedding-3-small",
                "entity_extraction": "gpt-5-nano",
                "summarization": "gpt-5-nano",
                "topic_modeling": "gpt-5-nano",
                "question_answering": "gpt-5-mini",
                "knowledge_synthesis": "gpt-5",
                "fallback": "gpt-4o-mini"
            },
            "limits": {
                "max_tokens_extraction": 5000  # High limit
            }
        }
        config = ModelConfig(high_limit_config)
        
        validation = config.validate_config()
        
        assert validation['valid'] is True  # Still valid, just warnings
        assert len(validation['warnings']) > 0
        
        # Check that high token limit is warned about
        warnings_text = " ".join(validation['warnings'])
        assert "High token limit" in warnings_text


class TestModelConfigFactories:
    """Test factory functions for ModelConfig."""
    
    @patch('app.model_config.get_default_model_config')
    def test_get_default_config(self, mock_get_default):
        """Test getting default configuration instance."""
        test_config = {"test": "config"}
        mock_get_default.return_value = test_config
        
        config = get_default_config()
        
        assert isinstance(config, ModelConfig)
        assert config.config == test_config
        mock_get_default.assert_called_once()
    
    def test_create_config_from_dict(self):
        """Test creating configuration from dictionary."""
        test_config = {"test": "config", "models": {"test": "model"}}
        
        config = create_config_from_dict(test_config)
        
        assert isinstance(config, ModelConfig)
        assert config.config == test_config


if __name__ == "__main__":
    pytest.main([__file__, "-v"])