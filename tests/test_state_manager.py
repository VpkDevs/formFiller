import pytest
import os
import json
import time
from utils.state_manager import StateManager
from datetime import datetime

@pytest.fixture
def state_manager(temp_dir):
    """Create a StateManager instance with temporary directory"""
    original_state_file = "data/app_state.json"
    original_backup_dir = "data/backups"
    
    # Create instance with temp locations
    manager = StateManager()
    manager.state_file = os.path.join(temp_dir, "app_state.json")
    manager.backup_dir = os.path.join(temp_dir, "backups")
    
    return manager

def test_default_state_creation(state_manager):
    """Test that default state is created correctly"""
    default_state = state_manager.get_default_state()
    
    # Check required keys exist
    assert "current_profile" in default_state
    assert "window_position" in default_state
    assert "window_size" in default_state
    assert "active_tab" in default_state
    assert "last_used_fields" in default_state
    assert "auto_save_enabled" in default_state
    assert "theme" in default_state
    assert "command_history" in default_state
    
    # Check default values
    assert default_state["current_profile"] == "default"
    assert default_state["auto_save_enabled"] == True
    assert isinstance(default_state["last_used_fields"], list)
    assert isinstance(default_state["command_history"], list)

def test_state_persistence(state_manager):
    """Test that state is saved and loaded correctly"""
    # Update state
    test_value = "test_profile"
    state_manager.update_state("current_profile", test_value)
    
    # Create new instance to test loading
    new_manager = StateManager()
    new_manager.state_file = state_manager.state_file
    new_manager.backup_dir = state_manager.backup_dir
    
    # Check value persisted
    assert new_manager.get_state_value("current_profile") == test_value

def test_auto_save_interval(state_manager):
    """Test auto-save interval functionality"""
    # Set short interval for testing
    state_manager.auto_save_interval = 0.1  # 100ms
    
    # Initial save
    state_manager.update_state("test_key", "test_value")
    initial_save_time = state_manager.last_save_time
    
    # Immediate update shouldn't trigger save
    state_manager.update_state("another_key", "another_value")
    assert state_manager.last_save_time == initial_save_time
    
    # Wait for interval
    time.sleep(0.2)
    
    # Update should now trigger save
    state_manager.update_state("third_key", "third_value")
    assert state_manager.last_save_time > initial_save_time

def test_backup_creation(state_manager):
    """Test backup creation functionality"""
    # Create initial state
    state_manager.update_state("test_key", "test_value")
    
    # Force backup creation
    state_manager.create_backup()
    
    # Check backup file exists
    backups = os.listdir(state_manager.backup_dir)
    assert len(backups) > 0
    assert all(f.startswith("state_backup_") for f in backups)

def test_backup_cleanup(state_manager):
    """Test cleanup of old backups"""
    # Create multiple backups
    for _ in range(10):
        state_manager.create_backup()
        time.sleep(0.1)  # Ensure unique timestamps
    
    # Check only 5 backups are kept
    backups = os.listdir(state_manager.backup_dir)
    assert len(backups) <= 5

def test_command_history(state_manager):
    """Test command history functionality"""
    # Add commands
    commands = [
        {"action": "update_field", "field": "name", "value": "John"},
        {"action": "delete_field", "field": "address"},
        {"action": "add_field", "field": "phone", "value": "123-456-7890"}
    ]
    
    for cmd in commands:
        state_manager.add_to_history(cmd)
    
    # Check history is maintained
    assert len(state_manager.command_history) == len(commands)
    
    # Test undo functionality
    last_command = state_manager.undo_last_command()
    assert last_command == commands[-1]
    assert len(state_manager.command_history) == len(commands) - 1

def test_history_limit(state_manager):
    """Test command history size limit"""
    # Add more commands than the limit
    for i in range(state_manager.max_history + 5):
        state_manager.add_to_history({"action": f"command_{i}"})
    
    # Check history is limited
    assert len(state_manager.command_history) == state_manager.max_history

def test_state_reset(state_manager):
    """Test state reset functionality"""
    # Add some state
    state_manager.update_state("test_key", "test_value")
    state_manager.add_to_history({"action": "test_command"})
    
    # Reset state
    state_manager.reset_state()
    
    # Check state is back to default
    assert state_manager.state == state_manager.get_default_state()
    assert len(state_manager.command_history) == 0

def test_concurrent_access(state_manager):
    """Test thread safety of state updates"""
    import threading
    
    def update_state(key, value):
        state_manager.update_state(key, value)
    
    # Create multiple threads updating state
    threads = []
    for i in range(10):
        t = threading.Thread(target=update_state, args=(f"key_{i}", f"value_{i}"))
        threads.append(t)
    
    # Start all threads
    for t in threads:
        t.start()
    
    # Wait for all threads to complete
    for t in threads:
        t.join()
    
    # Check all updates were saved
    for i in range(10):
        assert state_manager.get_state_value(f"key_{i}") == f"value_{i}"

def test_error_handling(state_manager, temp_dir):
    """Test error handling for file operations"""
    # Make state file directory read-only
    os.chmod(temp_dir, 0o444)
    
    try:
        # Attempt to save state should not raise exception
        result = state_manager.save_state()
        assert result == False
        
        # Attempt to create backup should not raise exception
        result = state_manager.create_backup()
        assert result == False
    finally:
        # Restore permissions for cleanup
        os.chmod(temp_dir, 0o777)
