import pytest
import tkinter as tk
from unittest.mock import Mock, patch
import json
import os
from main import FormAutofiller
from utils.validator import DataValidator  # Import the DataValidator

@pytest.fixture
def app():
    """Create a FormAutofiller instance with a test root window"""
    root = tk.Tk()
    app = FormAutofiller(root)
    yield app
    root.destroy()

# Existing test functions...

def test_user_registration_success(app):
    """Test successful user registration"""
    validator = DataValidator()
    username = "testuser"
    email = "test@example.com"
    password = "strongpassword"
    
    is_valid, error = validator.validate_user_registration(username, email, password)
    assert is_valid is True
    assert error is None

def test_user_registration_existing_email(app):
    """Test registration with an existing email"""
    # Simulate existing user
    existing_email = "existing@example.com"
    # Assume this email is already in the database
    # Here we would normally mock the database call to check for existing users
    
    validator = DataValidator()
    username = "newuser"
    password = "strongpassword"
    
    is_valid, error = validator.validate_user_registration(username, existing_email, password)
    assert is_valid is False
    assert error == "User already exists"

def test_user_registration_validation_errors(app):
    """Test validation errors during user registration"""
    validator = DataValidator()
    
    # Test short username
    is_valid, error = validator.validate_user_registration("us", "test@example.com", "strongpassword")
    assert is_valid is False
    assert error == "Username must be at least 3 characters long"
    
    # Test invalid email
    is_valid, error = validator.validate_user_registration("testuser", "invalid-email", "strongpassword")
    assert is_valid is False
    assert error == "Invalid email format"
    
    # Test weak password
    is_valid, error = validator.validate_user_registration("testuser", "test@example.com", "short")
    assert is_valid is False
    assert error == "Password must be at least 8 characters long"
