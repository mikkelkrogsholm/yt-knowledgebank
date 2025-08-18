import json
import os

SETTINGS_FILE = "/app/data/settings.json"

def get_api_key():
    """Get the ElevenLabs API key from settings."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                return settings.get('elevenlabs_api_key')
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    return None

def save_api_key(api_key: str):
    """Save the ElevenLabs API key to settings."""
    os.makedirs("/app/data", exist_ok=True)
    settings = {}
    
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            settings = {}
    
    settings['elevenlabs_api_key'] = api_key.strip()
    
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

def get_openai_api_key():
    """Get the OpenAI API key from settings."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                return settings.get('openai_api_key')
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    return None

def save_openai_api_key(api_key: str):
    """Save the OpenAI API key to settings."""
    os.makedirs("/app/data", exist_ok=True)
    settings = {}
    
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            settings = {}
    
    settings['openai_api_key'] = api_key.strip()
    
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

def get_model_config():
    """Get model configuration from settings."""
    settings = get_settings()
    return settings.get('model_config', get_default_model_config())

def save_model_config(config: dict):
    """Save model configuration to settings."""
    os.makedirs("/app/data", exist_ok=True)
    settings = {}
    
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            settings = {}
    
    settings['model_config'] = config
    
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

def get_default_model_config():
    """Return default GPT-5 model configuration."""
    return {
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

def get_settings():
    """Get all settings as a dictionary."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    return {}