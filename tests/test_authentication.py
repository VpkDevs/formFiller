import pytest
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def test_password_recovery():
    response = client.post("/password_recovery/", json={"email": "test@example.com"})
    assert response.status_code == 200
    assert response.json() == {"message": "Password reset link sent to your email."}

def test_user_registration():
    response = client.post("/register/", json={
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "StrongPassword123!"
    })
    assert response.status_code == 200
    assert response.json() == {"message": "User registered successfully. Please check your email for OTP and verification."}

    # Test registration with existing email
    response = client.post("/register/", json={
        "username": "anotheruser",
        "email": "newuser@example.com",  # Existing email
        "password": "AnotherStrongPassword123!"
    })
    assert response.status_code == 400
    assert response.json() == {"detail": "User already exists"}

def test_account_locking():
    for _ in range(5):  # Simulate 5 failed login attempts
        response = client.post("/login/", json={"username": "testuser", "password": "wrongpassword"})
        assert response.status_code == 401

    # Attempt to login after account is locked
    response = client.post("/login/", json={"username": "testuser", "password": "correctpassword"})
    assert response.status_code == 403
    assert response.json() == {"detail": "Account locked. Please try again later."}
