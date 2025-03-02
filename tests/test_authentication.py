import pytest
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def test_password_recovery():
    response = client.post("/password_recovery/", json={"email": "test@example.com"})
    assert response.status_code == 200
    assert response.json() == {"message": "Password reset link sent to your email."}

def test_account_locking():
    for _ in range(5):  # Simulate 5 failed login attempts
        response = client.post("/login/", json={"username": "testuser", "password": "wrongpassword"})
        assert response.status_code == 401

    # Attempt to login after account is locked
    response = client.post("/login/", json={"username": "testuser", "password": "correctpassword"})
    assert response.status_code == 403
    assert response.json() == {"detail": "Account locked. Please try again later."}
