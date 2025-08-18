"""
Model Configuration System for OpenAI API integration.
Provides smart model routing, cost optimization, and batch processing configuration.
"""

from typing import Dict, Any, Optional
from .settings import get_model_config, get_default_model_config


class ModelConfig:
    """Manages model selection and configuration for different AI tasks."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with configuration or use defaults."""
        self.config = config or get_model_config()
    
    def get_model_for_task(self, task_type: str) -> str:
        """Get the appropriate model for a specific task type."""
        models = self.config.get('models', {})
        return models.get(task_type, models.get('fallback', 'gpt-4o-mini'))
    
    def get_embedding_model(self) -> str:
        """Get the model for text embeddings."""
        return self.get_model_for_task('embedding')
    
    def get_extraction_model(self) -> str:
        """Get the model for entity extraction."""
        return self.get_model_for_task('entity_extraction')
    
    def get_summarization_model(self) -> str:
        """Get the model for text summarization."""
        return self.get_model_for_task('summarization')
    
    def get_topic_modeling_model(self) -> str:
        """Get the model for topic modeling."""
        return self.get_model_for_task('topic_modeling')
    
    def get_qa_model(self) -> str:
        """Get the model for question answering."""
        return self.get_model_for_task('question_answering')
    
    def get_synthesis_model(self) -> str:
        """Get the model for knowledge synthesis."""
        return self.get_model_for_task('knowledge_synthesis')
    
    def should_use_batch_processing(self) -> bool:
        """Check if batch processing should be used."""
        return self.config.get('processing_tiers', {}).get('batch', True)
    
    def should_use_cache(self) -> bool:
        """Check if caching should be used."""
        return self.config.get('processing_tiers', {}).get('use_cache', True)
    
    def should_optimize_costs(self) -> bool:
        """Check if cost optimization is enabled."""
        return self.config.get('processing_tiers', {}).get('cost_optimization', True)
    
    def get_max_tokens_for_task(self, task_type: str) -> int:
        """Get maximum tokens allowed for a specific task."""
        limits = self.config.get('limits', {})
        if task_type in ['entity_extraction', 'summarization', 'topic_modeling']:
            return limits.get('max_tokens_extraction', 1000)
        elif task_type in ['question_answering', 'knowledge_synthesis']:
            return limits.get('max_tokens_qa', 2000)
        else:
            return limits.get('max_tokens_extraction', 1000)
    
    def get_temperature_for_task(self, task_type: str) -> float:
        """Get temperature setting for a specific task."""
        limits = self.config.get('limits', {})
        if task_type in ['entity_extraction', 'summarization', 'topic_modeling']:
            return limits.get('temperature_extraction', 0.1)
        elif task_type in ['question_answering', 'knowledge_synthesis']:
            return limits.get('temperature_qa', 0.7)
        else:
            return limits.get('temperature_extraction', 0.1)
    
    def get_task_config(self, task_type: str) -> Dict[str, Any]:
        """Get complete configuration for a specific task."""
        return {
            'model': self.get_model_for_task(task_type),
            'max_tokens': self.get_max_tokens_for_task(task_type),
            'temperature': self.get_temperature_for_task(task_type),
            'use_batch': self.should_use_batch_processing(),
            'use_cache': self.should_use_cache()
        }
    
    def estimate_cost(self, task_type: str, input_tokens: int, output_tokens: int) -> Dict[str, float]:
        """Estimate cost for a specific task based on token usage."""
        model = self.get_model_for_task(task_type)
        
        # Cost estimates per 1M tokens (as of GPT-5 pricing)
        model_costs = {
            'gpt-5-nano': {'input': 2.0, 'output': 8.0},
            'gpt-5-mini': {'input': 3.0, 'output': 12.0},
            'gpt-5': {'input': 10.0, 'output': 30.0},
            'gpt-4o-mini': {'input': 0.15, 'output': 0.6},
            'text-embedding-3-small': {'input': 0.02, 'output': 0.0}
        }
        
        costs = model_costs.get(model, model_costs['gpt-4o-mini'])
        
        input_cost = (input_tokens / 1_000_000) * costs['input']
        output_cost = (output_tokens / 1_000_000) * costs['output']
        total_cost = input_cost + output_cost
        
        return {
            'input_cost': input_cost,
            'output_cost': output_cost,
            'total_cost': total_cost,
            'model': model
        }
    
    def get_cost_optimized_model(self, task_type: str, estimated_tokens: int) -> str:
        """Select the most cost-effective model for a task based on token count."""
        if not self.should_optimize_costs():
            return self.get_model_for_task(task_type)
        
        # For small tasks, use nano models
        if estimated_tokens < 500:
            if task_type in ['entity_extraction', 'summarization', 'topic_modeling']:
                return 'gpt-5-nano'
        
        # For medium tasks, use mini models  
        elif estimated_tokens < 2000:
            if task_type in ['question_answering']:
                return 'gpt-5-mini'
        
        # For large complex tasks, use full models
        elif task_type == 'knowledge_synthesis':
            return 'gpt-5'
        
        # Default to configured model
        return self.get_model_for_task(task_type)
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate the current configuration and return any issues."""
        issues = []
        warnings = []
        
        required_models = ['embedding', 'entity_extraction', 'summarization', 
                          'question_answering', 'fallback']
        
        models = self.config.get('models', {})
        for model_type in required_models:
            if model_type not in models:
                issues.append(f"Missing model configuration for '{model_type}'")
        
        # Check for deprecated models
        deprecated_models = ['gpt-4', 'gpt-3.5-turbo']
        for model_type, model_name in models.items():
            if model_name in deprecated_models:
                warnings.append(f"Model '{model_name}' for '{model_type}' may be deprecated")
        
        # Validate limits
        limits = self.config.get('limits', {})
        if limits.get('max_tokens_extraction', 0) > 4000:
            warnings.append("High token limit for extraction tasks may increase costs")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }


def get_default_config() -> ModelConfig:
    """Get default model configuration instance."""
    return ModelConfig(get_default_model_config())


def create_config_from_dict(config_dict: Dict[str, Any]) -> ModelConfig:
    """Create ModelConfig instance from dictionary."""
    return ModelConfig(config_dict)