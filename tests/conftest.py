import pytest
import os
import json
import tempfile
from pathlib import Path
from typing import Dict, Any

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname

@pytest.fixture
def sample_profile() -> Dict[str, Any]:
    """Return a sample profile for testing"""
    return {
        "personal": {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "+1 555-123-4567",
            "address": "123 Main St, Anytown, ST 12345",
            "ssn": "123-45-6789"
        },
        "payment": {
            "card_number": "4111111111111111",
            "card_name": "John Doe",
            "expiry_date": "12/25",
            "cvv": "123"
        },
        "preferences": {
            "newsletter": True,
            "dark_mode": False
        }
    }

@pytest.fixture
def mock_config(temp_dir) -> Dict[str, Any]:
    """Create a mock configuration for testing"""
    config = {
        "field_delay": 0.1,
        "key_delay": 0.05,
        "retry_attempts": 2,
        "hotkey": "ctrl+space"
    }
    
    config_path = Path(temp_dir) / "config.json"
    with open(config_path, 'w') as f:
        json.dump(config, f)
    
    return config

@pytest.fixture
def mock_field_mappings(temp_dir) -> Dict[str, Any]:
    """Create mock field mappings for testing"""
    mappings = {
        "custom_field": ["variation1", "variation2"],
        "another_field": ["var1", "var2", "var3"]
    }
    
    mappings_path = Path(temp_dir) / "field_mappings.json"
    with open(mappings_path, 'w') as f:
        json.dump(mappings, f)
    
    return mappings

@pytest.fixture
def mock_state_file(temp_dir, sample_profile):
    """Create a mock state file for testing"""
    state = {
        "current_profile": "default",
        "window_position": {"x": 0, "y": 0},
        "window_size": {"width": 800, "height": 800},
        "active_tab": 0,
        "last_used_fields": [],
        "auto_save_enabled": True,
        "theme": "default",
        "profiles": {
            "default": sample_profile
        }
    }
    
    state_path = Path(temp_dir) / "app_state.json"
    with open(state_path, 'w') as f:
        json.dump(state, f)
    
    return state

@pytest.fixture
def mock_encryption_key(temp_dir):
    """Create a mock encryption key for testing"""
    from cryptography.fernet import Fernet
    key = Fernet.generate_key()
    
    key_path = Path(temp_dir) / "test_master.key"
    with open(key_path, 'wb') as f:
        f.write(key)
    
    return key

@pytest.fixture
def mock_logger(temp_dir):
    """Set up a mock logger for testing"""
    import logging
    
    log_path = Path(temp_dir) / "test.log"
    handler = logging.FileHandler(log_path)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    logger = logging.getLogger('test_logger')
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
    return logger
