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

def get_settings():
    """Get all settings as a dictionary."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    return {}