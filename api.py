from fastapi import FastAPI, HTTPException, Depends, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, validator, Field
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
import uuid
import jwt
from .database import Database, get_user_by_email, save_user_to_db
from .email_service import send_verification_email
from .utils.validator import DataValidator
from .cloud.sync_manager import CloudSyncManager
from .ai.field_detector import AIFieldDetector
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
import hashlib
import os
from enum import Enum

# Enterprise Form Autofiller Pro API
app = FastAPI(
    title="Form Autofiller Pro Enterprise API",
    description="Professional form automation platform with AI-powered field detection, cloud sync, and enterprise security",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security
security = HTTPBearer()
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-here")
JWT_ALGORITHM = "HS256"

# Initialize AI field detector
ai_detector = AIFieldDetector()

# Role-based access control
class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    ENTERPRISE_ADMIN = "enterprise_admin"

# Enhanced models
class UserRegistration(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    password: str = Field(..., min_length=8)
    company: Optional[str] = None
    role: UserRole = UserRole.USER
    
    @validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v

class FormField(BaseModel):
    field_id: str
    field_type: str
    label: str
    value: str
    confidence: Optional[float] = None
    suggestions: Optional[List[str]] = []

class FormAnalysisRequest(BaseModel):
    url: str
    html_content: Optional[str] = None
    fields_data: Optional[List[Dict[str, Any]]] = []

class ProfileData(BaseModel):
    profile_id: Optional[str] = None
    name: str
    personal_info: Dict[str, Any] = {}
    professional_info: Dict[str, Any] = {}
    financial_info: Dict[str, Any] = {}
    custom_fields: Dict[str, Any] = {}
    shared_with: List[str] = []
    tags: List[str] = []

class AuditLogEntry(BaseModel):
    timestamp: datetime
    user_id: str
    action: str
    resource: str
    details: Dict[str, Any]
    ip_address: str
    user_agent: Optional[str] = None
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

# Authentication and authorization
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and return user info"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

def require_role(required_role: UserRole):
    """Decorator to require specific role"""
    def role_checker(current_user: dict = Depends(verify_token)):
        user_role = current_user.get("role", UserRole.GUEST)
        if user_role != required_role and user_role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker

# Audit logging
audit_logs = []  # In production, use proper database

def audit_log(event: str, username: str = None, email: str = None, ip: str = None, details: Dict = None):
    """Log sensitive operations for auditing purposes."""
    log_entry = AuditLogEntry(
        timestamp=datetime.utcnow(),
        user_id=username or "unknown",
        action=event,
        resource="api",
        details=details or {},
        ip_address=ip or "unknown"
    )
    audit_logs.append(log_entry)
    logging.info(f"AUDIT: {event} - User: {username or 'N/A'}, Email: {email or 'N/A'}, IP: {ip or 'N/A'}")

# API Endpoints
@app.post("/auth/register")
@limiter.limit("5/minute")
async def register_user(user: UserRegistration, request: Request, response: Response):
    """Enhanced user registration with enterprise features"""
    try:
        # Validate input
        validator = DataValidator()
        if not validator.is_valid_email(user.email):
            raise HTTPException(status_code=400, detail="Invalid email format")
        
        # Check if user already exists
        # existing_user = await get_user_by_email(user.email)
        # if existing_user:
        #     raise HTTPException(status_code=400, detail="User already exists")
        
        # Hash password
        password_hash = hashlib.sha256(user.password.encode()).hexdigest()
        
        # Create user ID
        user_id = str(uuid.uuid4())
        
        # Generate verification token
        verification_token = str(uuid.uuid4())
        
        # Save user to database (pseudo-code)
        # await save_user_to_db(
        #     user_id=user_id,
        #     username=user.username,
        #     email=user.email,
        #     password_hash=password_hash,
        #     role=user.role,
        #     company=user.company,
        #     verification_token=verification_token
        # )
        
        # Generate OTP
        otp = str(random.randint(100000, 999999))
        
        # Send verification email
        send_verification_email(user.email, otp)
        
        # Create access token
        access_token = create_access_token(
            data={"sub": user_id, "username": user.username, "role": user.role}
        )
        
        # Set secure cookie
        response.set_cookie(
            "access_token",
            access_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=86400  # 24 hours
        )
        
        audit_log(
            event="user_registration",
            username=user.username,
            email=user.email,
            ip=request.client.host,
            details={"company": user.company, "role": user.role}
        )
        
        return {
            "message": "User registered successfully. Please verify your email.",
            "user_id": user_id,
            "access_token": access_token
        }
        
    except HTTPException as e:
        logging.error(f"Registration HTTPException: {e}")
        raise e
    except Exception as e:
        logging.exception(f"Registration unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/analyze-form")
async def analyze_form(
    analysis_request: FormAnalysisRequest,
    current_user: dict = Depends(verify_token)
):
    """AI-powered form field analysis"""
    try:
        results = []
        
        if analysis_request.fields_data:
            # Use AI detector for batch analysis
            detection_results = ai_detector.batch_analyze_fields(analysis_request.fields_data)
            
            for result in detection_results:
                results.append({
                    "field_name": result.field_name,
                    "detected_type": result.detected_type,
                    "confidence_score": result.confidence_score,
                    "suggestions": result.suggestions,
                    "context_clues": result.context_clues,
                    "semantic_category": result.semantic_category
                })
        
        audit_log(
            event="form_analysis",
            username=current_user.get("username"),
            details={
                "url": analysis_request.url,
                "fields_analyzed": len(analysis_request.fields_data or [])
            }
        )
        
        return {
            "analysis_results": results,
            "url": analysis_request.url,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Form analysis error: {e}")
        raise HTTPException(status_code=500, detail="Form analysis failed")

@app.post("/profiles")
async def create_profile(
    profile: ProfileData,
    current_user: dict = Depends(verify_token)
):
    """Create a new form-filling profile"""
    try:
        profile_id = str(uuid.uuid4())
        profile.profile_id = profile_id
        
        # Add metadata
        profile_data = profile.dict()
        profile_data.update({
            "created_by": current_user.get("sub"),
            "created_at": datetime.utcnow().isoformat(),
            "last_modified": datetime.utcnow().isoformat(),
            "version": 1
        })
        
        # TODO: Save to database
        # await save_profile_to_db(profile_data)
        
        audit_log(
            event="profile_created",
            username=current_user.get("username"),
            details={"profile_id": profile_id, "profile_name": profile.name}
        )
        
        return {
            "profile_id": profile_id,
            "message": "Profile created successfully"
        }
        
    except Exception as e:
        logging.error(f"Profile creation error: {e}")
        raise HTTPException(status_code=500, detail="Profile creation failed")

@app.get("/profiles")
async def list_profiles(
    current_user: dict = Depends(verify_token),
    limit: int = 50,
    offset: int = 0
):
    """List user's profiles with pagination"""
    try:
        user_id = current_user.get("sub")
        
        # TODO: Fetch from database
        # profiles = await get_user_profiles(user_id, limit, offset)
        profiles = []  # Placeholder
        
        return {
            "profiles": profiles,
            "total": len(profiles),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logging.error(f"Profile listing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to list profiles")

@app.get("/profiles/{profile_id}")
async def get_profile(
    profile_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get a specific profile"""
    try:
        # TODO: Fetch from database and check permissions
        # profile = await get_profile_by_id(profile_id, current_user.get("sub"))
        
        # if not profile:
        #     raise HTTPException(status_code=404, detail="Profile not found")
        
        audit_log(
            event="profile_accessed",
            username=current_user.get("username"),
            details={"profile_id": profile_id}
        )
        
        return {"message": "Profile retrieved successfully"}  # Placeholder
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Profile retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Profile retrieval failed")

@app.put("/profiles/{profile_id}")
async def update_profile(
    profile_id: str,
    profile: ProfileData,
    current_user: dict = Depends(verify_token)
):
    """Update an existing profile"""
    try:
        # TODO: Check ownership/permissions and update in database
        
        audit_log(
            event="profile_updated",
            username=current_user.get("username"),
            details={"profile_id": profile_id, "profile_name": profile.name}
        )
        
        return {"message": "Profile updated successfully"}
        
    except Exception as e:
        logging.error(f"Profile update error: {e}")
        raise HTTPException(status_code=500, detail="Profile update failed")

@app.delete("/profiles/{profile_id}")
async def delete_profile(
    profile_id: str,
    current_user: dict = Depends(verify_token)
):
    """Delete a profile"""
    try:
        # TODO: Check ownership and delete from database
        
        audit_log(
            event="profile_deleted",
            username=current_user.get("username"),
            details={"profile_id": profile_id}
        )
        
        return {"message": "Profile deleted successfully"}
        
    except Exception as e:
        logging.error(f"Profile deletion error: {e}")
        raise HTTPException(status_code=500, detail="Profile deletion failed")

@app.post("/profiles/{profile_id}/share")
async def share_profile(
    profile_id: str,
    share_request: dict,
    current_user: dict = Depends(verify_token)
):
    """Share a profile with other users"""
    try:
        user_email = share_request.get("user_email")
        permissions = share_request.get("permissions", "read")
        
        # TODO: Implement sharing logic
        
        audit_log(
            event="profile_shared",
            username=current_user.get("username"),
            details={
                "profile_id": profile_id,
                "shared_with": user_email,
                "permissions": permissions
            }
        )
        
        return {"message": f"Profile shared with {user_email}"}
        
    except Exception as e:
        logging.error(f"Profile sharing error: {e}")
        raise HTTPException(status_code=500, detail="Profile sharing failed")

@app.get("/admin/audit-logs")
async def get_audit_logs(
    current_user: dict = Depends(require_role(UserRole.ADMIN)),
    limit: int = 100,
    offset: int = 0
):
    """Get audit logs (admin only)"""
    try:
        # Return recent audit logs
        logs = audit_logs[-limit-offset:-offset] if offset > 0 else audit_logs[-limit:]
        
        return {
            "logs": [log.dict() for log in reversed(logs)],
            "total": len(audit_logs),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logging.error(f"Audit log retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve audit logs")

@app.get("/admin/compliance-report")
async def generate_compliance_report(
    current_user: dict = Depends(require_role(UserRole.ADMIN)),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Generate GDPR/CCPA compliance report"""
    try:
        # TODO: Generate comprehensive compliance report
        
        report = {
            "report_id": str(uuid.uuid4()),
            "generated_at": datetime.utcnow().isoformat(),
            "generated_by": current_user.get("username"),
            "period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "summary": {
                "total_users": 0,  # TODO: Get from database
                "data_requests": 0,
                "data_deletions": 0,
                "security_incidents": 0
            },
            "compliance_status": "compliant"  # TODO: Calculate based on actual data
        }
        
        audit_log(
            event="compliance_report_generated",
            username=current_user.get("username"),
            details={"report_id": report["report_id"]}
        )
        
        return report
        
    except Exception as e:
        logging.error(f"Compliance report error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate compliance report")

# Health check and monitoring
@app.get("/health")
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "features": {
            "ai_detection": True,
            "cloud_sync": True,
            "browser_automation": True,
            "ocr_processing": True,
            "enterprise_security": True
        }
    }

# Metrics endpoint
@app.get("/metrics")
async def get_metrics(
    current_user: dict = Depends(require_role(UserRole.ADMIN))
):
    """Get system metrics (admin only)"""
    return {
        "active_users": 0,  # TODO: Get from database
        "total_profiles": 0,
        "forms_filled_today": 0,
        "ai_detection_accuracy": 0.95,
        "system_uptime": "99.9%",
        "security_incidents": 0
    }

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
