class FormAutofillerError(Exception):
    """Base exception for all application errors"""
    pass

class ValidationError(FormAutofillerError):
    """Raised when data validation fails"""
    def __init__(self, field: str, value: str, reason: str):
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"Validation failed for {field}: {reason}")

class SecurityError(FormAutofillerError):
    """Raised when security operations fail"""
    pass

class StateError(FormAutofillerError):
    """Raised when state operations fail"""
    pass

class ProfileError(FormAutofillerError):
    """Raised when profile operations fail"""
    pass