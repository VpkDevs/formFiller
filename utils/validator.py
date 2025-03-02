import re
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
import phonenumbers
from postal.parser import parse_address
import logging

class DataValidator:
    def __init__(self):
        self.validation_patterns = {
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'phone': r'^\+?1?\d{9,15}$',
            'zip': r'^\d{5}(-\d{4})?$',
            'ssn': r'^\d{3}-\d{2}-\d{4}$',
            'card_number': r'^\d{13,19}$',
            'cvv': r'^\d{3,4}$',
            'expiry_date': r'^(0[1-9]|1[0-2])/([0-9]{2})$',
            'url': r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
        }
        
        self.field_formats = {
            'phone': '(XXX) XXX-XXXX or +X XXX XXX XXXX',
            'ssn': 'XXX-XX-XXXX',
            'zip': 'XXXXX or XXXXX-XXXX',
            'card_number': 'XXXX XXXX XXXX XXXX',
            'expiry_date': 'MM/YY',
            'dob': 'MM/DD/YYYY'
        }
    
    # Existing validation methods...

    def validate_user_registration(self, username: str, email: str, password: str) -> Tuple[bool, Optional[str]]:
        """Validate user registration inputs"""
        if not username or len(username) < 3:
            return False, "Username must be at least 3 characters long"
        
        email_valid, email_error = self._validate_email(email)
        if not email_valid:
            return False, email_error
        
        if not password or len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        password_strength, password_error = self._check_password_strength(password)
        if not password_strength:
            return False, password_error
        
        return True, None
    
    def _check_password_strength(self, password: str) -> Tuple[bool, Optional[str]]:
        """Check password strength based on complexity rules"""
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r"\d", password):
            return False, "Password must contain at least one digit"
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False, "Password must contain at least one special character"
        return True, None
