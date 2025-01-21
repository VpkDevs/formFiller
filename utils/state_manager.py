import json
import os
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
import shutil
import logging
from threading import Lock

class StateManager:
    def __init__(self, auto_save_interval: int = 300):  # 5 minutes default
        self.state_file = "data/app_state.json"
        self.backup_dir = "data/backups"
        self.auto_save_interval = auto_save_interval
        self.last_save_time = time.time()
        self.state_lock = Lock()
        self.command_history: List[Dict[str, Any]] = []
        self.max_history = 50
        
        # Create necessary directories
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Initialize state
        self.state = self.load_state()
    
    def load_state(self) -> Dict[str, Any]:
        """Load application state from file or return default state"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Error loading state: {str(e)}")
            # Try to load from backup
            return self.restore_from_backup()
        
        return self.get_default_state()
    
    def get_default_state(self) -> Dict[str, Any]:
        """Return default application state"""
        return {
            "current_profile": "default",
            "window_position": {"x": 0, "y": 0},
            "window_size": {"width": 800, "height": 800},
            "active_tab": 0,
            "last_used_fields": [],
            "auto_save_enabled": True,
            "last_backup": None,
            "theme": "default",
            "command_history": []
        }
    
    def save_state(self, force: bool = False) -> bool:
        """Save current application state"""
        current_time = time.time()
        
        # Check if we should auto-save
        if not force and (current_time - self.last_save_time) < self.auto_save_interval:
            return False
            
        with self.state_lock:
            try:
                # Create backup before saving
                if os.path.exists(self.state_file):
                    self.create_backup()
                
                # Update last save time
                self.state["last_saved"] = datetime.now().isoformat()
                
                # Save state
                with open(self.state_file, 'w') as f:
                    json.dump(self.state, f, indent=4)
                
                self.last_save_time = current_time
                return True
            except Exception as e:
                logging.error(f"Error saving state: {str(e)}")
                return False
    
    def create_backup(self) -> bool:
        """Create a backup of the current state file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.backup_dir, f"state_backup_{timestamp}.json")
            shutil.copy2(self.state_file, backup_file)
            
            # Update last backup time
            self.state["last_backup"] = timestamp
            
            # Clean old backups (keep last 5)
            self._clean_old_backups()
            return True
        except Exception as e:
            logging.error(f"Error creating backup: {str(e)}")
            return False
    
    def restore_from_backup(self) -> Dict[str, Any]:
        """Restore state from most recent backup"""
        try:
            backups = sorted([f for f in os.listdir(self.backup_dir) if f.startswith("state_backup_")])
            if backups:
                latest_backup = os.path.join(self.backup_dir, backups[-1])
                with open(latest_backup, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Error restoring from backup: {str(e)}")
        
        return self.get_default_state()
    
    def _clean_old_backups(self, keep_count: int = 5):
        """Remove old backups keeping only the most recent ones"""
        try:
            backups = sorted([f for f in os.listdir(self.backup_dir) if f.startswith("state_backup_")])
            if len(backups) > keep_count:
                for old_backup in backups[:-keep_count]:
                    os.remove(os.path.join(self.backup_dir, old_backup))
        except Exception as e:
            logging.error(f"Error cleaning old backups: {str(e)}")
    
    def update_state(self, key: str, value: Any) -> bool:
        """Update a specific state value"""
        with self.state_lock:
            try:
                self.state[key] = value
                return self.save_state()
            except Exception as e:
                logging.error(f"Error updating state: {str(e)}")
                return False
    
    def add_to_history(self, command: Dict[str, Any]):
        """Add command to history with undo/redo support"""
        self.command_history.append(command)
        if len(self.command_history) > self.max_history:
            self.command_history.pop(0)
        self.update_state("command_history", self.command_history)
    
    def undo_last_command(self) -> Optional[Dict[str, Any]]:
        """Retrieve the last command for undo operation"""
        if self.command_history:
            command = self.command_history.pop()
            self.update_state("command_history", self.command_history)
            return command
        return None
    
    def get_state_value(self, key: str, default: Any = None) -> Any:
        """Get a specific state value"""
        return self.state.get(key, default)
    
    def reset_state(self) -> bool:
        """Reset state to default values"""
        self.state = self.get_default_state()
        return self.save_state(force=True)
