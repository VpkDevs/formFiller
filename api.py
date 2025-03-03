from fastapi import FastAPI, HTTPException, Depends, Request, Response
from pydantic import BaseModel, validator
from typing import Dict, Optional
from .database import Database, get_user_by_email, save_user_to_db
from .email_service import send_verification_email
from .database import Database, get_user_by_email, save_user_to_db
from .utils.validator import DataValidator
import random
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from bleach import clean
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
import re

app = FastAPI(title="Form Autofiller API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class UserRegistration(BaseModel):
    username: str
    email: str
    password: str
    
    @validator("username")
    def username_must_be_alphanumeric(cls, username):
        if not username.isalnum():
            raise ValueError("Username must be alphanumeric")
        return username

    @validator("email")
    def email_must_be_valid(cls, email):
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            raise ValueError("Invalid email format")
        return email

    @validator("password")
    def password_must_be_strong(cls, password):
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[a-z]", password):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[A-Z]", password):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"\d", password):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            raise ValueError("Password must contain at least one special character")
        return password

SESSION_TOKEN = "session_token"
FAILED_LOGIN_ATTEMPTS = {}
ACCOUNT_LOCK_TIMEOUT = 60  # seconds

def audit_log(event: str, username: str = None, email: str = None, ip: str = None):
    """Log sensitive operations for auditing purposes."""
    logging.info(f"AUDIT: {event} - User: {username or 'N/A'}, Email: {email or 'N/A'}, IP: {ip or 'N/A'}")

@app.post("/register/")
@limiter.limit("5/minute")
async def register_user(user: UserRegistration, request: Request, response: Response):
    try:
        # Sanitize user inputs
        user.username = clean(user.username)
        user.email = clean(user.email)
        user.password = clean(user.password)

        # Validate user registration inputs
        try:
            UserRegistration(**user.dict())
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        with Database("your_connection_string_here").session() as session:
            existing_user = get_user_by_email(session, user.email)
            if existing_user:
                raise HTTPException(status_code=400, detail="User already exists")
        
        # Hash the password
        import bcrypt
        hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
        
        # Save user to the database
        save_user_to_db(session, username=user.username, email=user.email, password=hashed_password.decode('utf-8'))

        # Hash the password (pseudo-code)
        # hashed_password = hash_password(user.password)

        # Save user to the database (pseudo-code)
        # await save_user_to_db(username=user.username, email=user.email, password=hashed_password)

        # Generate and send OTP (pseudo-code)
        # otp = generate_otp()
        # send_otp(user.email, otp)

        # Create session (pseudo-code)
        session_token = "generate_session_token()"
        response.set_cookie(SESSION_TOKEN, session_token, httponly=True, samesite="none", secure=True)

        # Generate OTP (for demonstration purposes, using a simple random number)
        otp = str(random.randint(100000, 999999))
        
        # Send verification email
        send_verification_email(user.email, otp)

        audit_log(event="User registration", username=user.username, email=user.email, ip=request.client.host)
        return {"message": "User registered successfully. Please check your email for OTP and verification."}
    except HTTPException as e:
        logging.error(f"HTTPException: {e}")
        raise e
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Password recovery endpoint (pseudo-code)
# @app.post("/password_recovery/")
# async def password_recovery(email: str):
#     try:
#         # Check if user exists (pseudo-code)
#         # existing_user = await get_user_by_email(email)
#         # if not existing_user:
#         #     raise HTTPException(status_code=404, detail="User not found")

#         # Generate and send password reset token (pseudo-code)
#         # reset_token = generate_reset_token()
#         # send_reset_token(email, reset_token)

#         return {"message": "Password reset link sent to your email."}
#     except Exception as e:
#         logging.exception(f"Unexpected error: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# Login endpoint (pseudo-code)
# @app.post("/login/")
# async def login(username: str, password: str, request: Request, response: Response):
#     try:
#         # Check if account is locked
#         if username in FAILED_LOGIN_ATTEMPTS and FAILED_LOGIN_ATTEMPTS[username]["lock_until"] > time.time():
#             raise HTTPException(status_code=403, detail="Account locked. Please try again later.")

#         # Validate user credentials (pseudo-code)
#         # user = await authenticate_user(username, password)
#         # if not user:
#         #     # Increment failed login attempts
#         #     if username not in FAILED_LOGIN_ATTEMPTS:
#         #         FAILED_LOGIN_ATTEMPTS[username] = {"attempts": 0, "lock_until": 0}
#         #     FAILED_LOGIN_ATTEMPTS[username]["attempts"] += 1

#         #     # Lock account after multiple failed attempts
#         #     if FAILED_LOGIN_ATTEMPTS[username]["attempts"] >= 5:
#         #         FAILED_LOGIN_ATTEMPTS[username]["lock_until"] = time.time() + ACCOUNT_LOCK_TIMEOUT
#         #         logging.warning(f"Account locked for user: {username}")
#         #         raise HTTPException(status_code=403, detail="Invalid credentials. Account locked.")

#         #     raise HTTPException(status_code=401, detail="Invalid credentials")

#         # Reset failed login attempts on successful login
#         # if username in FAILED_LOGIN_ATTEMPTS:
#         #     del FAILED_LOGIN_ATTEMPTS[username]

#         # Create session (pseudo-code)
#         session_token = "generate_session_token()"
#         response.set_cookie(SESSION_TOKEN, session_token, httponly=True, samesite="none", secure=True)

#         return {"message": "Login successful"}
#     except HTTPException as e:
#         logging.error(f"HTTPException: {e}")
#         raise e
#     except Exception as e:
#         logging.exception(f"Unexpected error: {e}")
#         raise HTTPException(status_code=500, detail=str(e))
