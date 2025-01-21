import pytest
from utils.validator import DataValidator

def test_email_validation():
    validator = DataValidator()
    
    # Valid emails
    assert validator.validate_field('email', 'test@example.com')[0] == True
    assert validator.validate_field('email', 'user.name+tag@example.co.uk')[0] == True
    
    # Invalid emails
    assert validator.validate_field('email', 'invalid.email')[0] == False
    assert validator.validate_field('email', '@example.com')[0] == False
    assert validator.validate_field('email', 'test@')[0] == False

def test_phone_validation():
    validator = DataValidator()
    
    # Valid phone numbers
    assert validator.validate_field('phone', '+1 555-123-4567')[0] == True
    assert validator.validate_field('phone', '(555) 123-4567')[0] == True
    
    # Invalid phone numbers
    assert validator.validate_field('phone', '123')[0] == False
    assert validator.validate_field('phone', 'abc-def-ghij')[0] == False

def test_card_number_validation():
    validator = DataValidator()
    
    # Valid card number (using test numbers)
    assert validator.validate_field('card_number', '4111111111111111')[0] == True  # Visa test number
    assert validator.validate_field('card_number', '5555555555554444')[0] == True  # Mastercard test number
    
    # Invalid card numbers
    assert validator.validate_field('card_number', '411111111111')[0] == False  # Too short
    assert validator.validate_field('card_number', 'abcd1234efgh5678')[0] == False  # Contains letters

def test_ssn_validation():
    validator = DataValidator()
    
    # Valid SSN
    assert validator.validate_field('ssn', '123-45-6789')[0] == True
    
    # Invalid SSN
    assert validator.validate_field('ssn', '123456789')[0] == False
    assert validator.validate_field('ssn', '123-45-678')[0] == False

def test_date_validation():
    validator = DataValidator()
    
    # Valid dates
    assert validator.validate_field('dob', '01/01/1990')[0] == True
    assert validator.validate_field('dob', '12/31/2000')[0] == True
    
    # Invalid dates
    assert validator.validate_field('dob', '13/01/1990')[0] == False  # Invalid month
    assert validator.validate_field('dob', '01/32/1990')[0] == False  # Invalid day
    assert validator.validate_field('dob', '01/01/2025')[0] == False  # Future date

def test_name_validation():
    validator = DataValidator()
    
    # Valid names
    assert validator.validate_field('name', 'John Doe')[0] == True
    assert validator.validate_field('name', "Mary Jane O'Connor")[0] == True
    
    # Invalid names
    assert validator.validate_field('name', '123')[0] == False
    assert validator.validate_field('name', 'J@hn D#e')[0] == False

def test_url_validation():
    validator = DataValidator()
    
    # Valid URLs
    assert validator.validate_field('url', 'https://www.example.com')[0] == True
    assert validator.validate_field('url', 'http://subdomain.example.co.uk/path')[0] == True
    
    # Invalid URLs
    assert validator.validate_field('url', 'not-a-url')[0] == False
    assert validator.validate_field('url', 'ftp://example.com')[0] == False

def test_value_standardization():
    validator = DataValidator()
    
    # Phone standardization
    assert validator.standardize_value('phone', '5551234567') == '+1 555-123-4567'
    
    # Name standardization
    assert validator.standardize_value('name', 'john doe') == 'John Doe'
    
    # Email standardization
    assert validator.standardize_value('email', 'Test@Example.COM') == 'test@example.com'
