from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import json
from typing import Dict, Any, Optional

class SecurityManager:
    def __init__(self, key_file: str = "security/master.key"):
        self.key_file = key_file
        self.key = self._load_or_create_key()
        self.fernet = Fernet(self.key)
        
    def _load_or_create_key(self) -> bytes:
        """Load existing key or create a new one"""
        try:
            with open(self.key_file, 'rb') as f:
                return f.read()
        except FileNotFoundError:
            key = Fernet.generate_key()
            os.makedirs(os.path.dirname(self.key_file), exist_ok=True)
            with open(self.key_file, 'wb') as f:
                f.write(key)
            return key
    
    def encrypt_value(self, value: str) -> str:
        """Encrypt a single value"""
        if not value:
            return value
        return base64.b64encode(
            self.fernet.encrypt(value.encode())
        ).decode('utf-8')
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a single value"""
        if not encrypted_value:
            return encrypted_value
        try:
            return self.fernet.decrypt(
                base64.b64decode(encrypted_value.encode())
            ).decode('utf-8')
        except Exception:
            return encrypted_value
    
    def encrypt_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive fields in a profile"""
        sensitive_fields = {
            'personal': ['ssn', 'passport', 'driver_license'],
            'payment': ['card_number', 'cvv']
        }
        
        encrypted_profile = profile.copy()
        
        for section, fields in sensitive_fields.items():
            if section in encrypted_profile:
                for field in fields:
                    if field in encrypted_profile[section]:
                        encrypted_profile[section][field] = self.encrypt_value(
                            encrypted_profile[section][field]
                        )
        
        return encrypted_profile
    
    def decrypt_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive fields in a profile"""
        sensitive_fields = {
            'personal': ['ssn', 'passport', 'driver_license'],
            'payment': ['card_number', 'cvv']
        }
        
        decrypted_profile = profile.copy()
        
        for section, fields in sensitive_fields.items():
            if section in decrypted_profile:
                for field in fields:
                    if field in decrypted_profile[section]:
                        decrypted_profile[section][field] = self.decrypt_value(
                            decrypted_profile[section][field]
                        )
        
        return decrypted_profile
    
    def secure_wipe(self, filepath: str) -> bool:
        """Securely wipe a file by overwriting with random data before deletion"""
        try:
            if os.path.exists(filepath):
                # Overwrite file with random data multiple times
                file_size = os.path.getsize(filepath)
                for _ in range(3):  # DoD recommends at least 3 passes
                    with open(filepath, 'wb') as f:
                        f.write(os.urandom(file_size))
                # Finally delete the file
                os.remove(filepath)
            return True
        except Exception:
            return False

    @staticmethod
    def mask_sensitive_value(value: str, show_chars: int = 4) -> str:
        """Mask sensitive data showing only last few characters"""
        if not value or len(value) <= show_chars:
            return value
        return '*' * (len(value) - show_chars) + value[-show_chars:]
