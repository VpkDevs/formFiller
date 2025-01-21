import pytest
import os
from security.encryption import SecurityManager

@pytest.fixture
def security_manager(temp_dir):
    """Create a SecurityManager instance with a temporary key file"""
    key_file = os.path.join(temp_dir, "test_master.key")
    return SecurityManager(key_file=key_file)

def test_key_generation(temp_dir):
    """Test that a new key is generated when none exists"""
    key_file = os.path.join(temp_dir, "test_master.key")
    manager = SecurityManager(key_file=key_file)
    
    # Check that key file was created
    assert os.path.exists(key_file)
    
    # Check that key is valid format
    with open(key_file, 'rb') as f:
        key = f.read()
    assert len(key) == 32  # Fernet keys are 32 bytes

def test_value_encryption(security_manager):
    """Test encryption and decryption of single values"""
    original = "sensitive data"
    encrypted = security_manager.encrypt_value(original)
    
    # Check that encrypted value is different from original
    assert encrypted != original
    
    # Check that decryption returns original value
    decrypted = security_manager.decrypt_value(encrypted)
    assert decrypted == original

def test_empty_value_handling(security_manager):
    """Test handling of empty values"""
    # Empty string should remain empty
    assert security_manager.encrypt_value("") == ""
    assert security_manager.decrypt_value("") == ""
    
    # None should be handled gracefully
    assert security_manager.encrypt_value(None) == None
    assert security_manager.decrypt_value(None) == None

def test_profile_encryption(security_manager, sample_profile):
    """Test encryption of sensitive fields in a profile"""
    encrypted_profile = security_manager.encrypt_profile(sample_profile)
    
    # Check that sensitive fields are encrypted
    assert encrypted_profile['personal']['ssn'] != sample_profile['personal']['ssn']
    assert encrypted_profile['payment']['card_number'] != sample_profile['payment']['card_number']
    assert encrypted_profile['payment']['cvv'] != sample_profile['payment']['cvv']
    
    # Check that non-sensitive fields remain unchanged
    assert encrypted_profile['personal']['first_name'] == sample_profile['personal']['first_name']
    assert encrypted_profile['personal']['email'] == sample_profile['personal']['email']
    
    # Test decryption
    decrypted_profile = security_manager.decrypt_profile(encrypted_profile)
    assert decrypted_profile == sample_profile

def test_secure_wipe(security_manager, temp_dir):
    """Test secure file wiping"""
    # Create a test file
    test_file = os.path.join(temp_dir, "test_file.txt")
    with open(test_file, 'w') as f:
        f.write("sensitive data")
    
    # Verify file exists
    assert os.path.exists(test_file)
    
    # Wipe file
    result = security_manager.secure_wipe(test_file)
    assert result == True
    
    # Verify file no longer exists
    assert not os.path.exists(test_file)

def test_mask_sensitive_value():
    """Test masking of sensitive values"""
    # Test with default show_chars=4
    assert SecurityManager.mask_sensitive_value("1234567890") == "******7890"
    
    # Test with custom show_chars
    assert SecurityManager.mask_sensitive_value("1234567890", show_chars=2) == "********90"
    
    # Test with short values
    assert SecurityManager.mask_sensitive_value("123") == "123"  # Too short to mask
    
    # Test with empty values
    assert SecurityManager.mask_sensitive_value("") == ""
    assert SecurityManager.mask_sensitive_value(None) == None

def test_key_persistence(temp_dir):
    """Test that encryption key persists between instances"""
    key_file = os.path.join(temp_dir, "test_master.key")
    
    # Create first instance and encrypt data
    manager1 = SecurityManager(key_file=key_file)
    encrypted = manager1.encrypt_value("test data")
    
    # Create second instance with same key file
    manager2 = SecurityManager(key_file=key_file)
    
    # Second instance should be able to decrypt data from first instance
    decrypted = manager2.decrypt_value(encrypted)
    assert decrypted == "test data"

def test_invalid_encrypted_data(security_manager):
    """Test handling of invalid encrypted data"""
    # Try to decrypt invalid base64 data
    result = security_manager.decrypt_value("not-encrypted-data")
    assert result == "not-encrypted-data"  # Should return original value
    
    # Try to decrypt empty string
    assert security_manager.decrypt_value("") == ""

def test_profile_encryption_idempotency(security_manager, sample_profile):
    """Test that multiple encryptions don't compound"""
    # Encrypt profile multiple times
    profile1 = security_manager.encrypt_profile(sample_profile)
    profile2 = security_manager.encrypt_profile(profile1)
    
    # Decrypt once
    decrypted = security_manager.decrypt_profile(profile2)
    
    # Should match original
    assert decrypted == sample_profile
