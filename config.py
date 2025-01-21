from dataclasses import dataclass
from typing import Dict, Any
import yaml
import os

@dataclass
class SecurityConfig:
    key_file: str
    encryption_algorithm: str
    key_rotation_days: int

@dataclass
class StateConfig:
    auto_save_interval: int
    max_history: int
    backup_count: int

@dataclass
class FormFillerConfig:
    field_delay: float
    key_delay: float
    retry_attempts: int
    default_hotkey: str

@dataclass
class AppConfig:
    security: SecurityConfig
    state: StateConfig
    form_filler: FormFillerConfig
    
    @classmethod
    def load(cls, config_path: str) -> 'AppConfig':
        if not os.path.exists(config_path):
            return cls.get_default()
            
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
            
        return cls(
            security=SecurityConfig(**config_data['security']),
            state=StateConfig(**config_data['state']),
            form_filler=FormFillerConfig(**config_data['form_filler'])
        )
    
    @classmethod
    def get_default(cls) -> 'AppConfig':
        return cls(
            security=SecurityConfig(
                key_file="security/master.key",
                encryption_algorithm="fernet",
                key_rotation_days=90
            ),
            state=StateConfig(
                auto_save_interval=300,
                max_history=50,
                backup_count=5
            ),
            form_filler=FormFillerConfig(
                field_delay=0.2,
                key_delay=0.05,
                retry_attempts=3,
                default_hotkey="ctrl+space"
            )
        )