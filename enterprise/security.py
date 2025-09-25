"""
Enterprise Security and Compliance Module
Provides GDPR/CCPA compliance, audit logging, role-based access control,
and advanced security features for enterprise deployments.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import os
import sqlite3
import threading
import time
import uuid
import jwt
from cryptography.fernet import Fernet
import requests


class ComplianceStandard(Enum):
    """Supported compliance standards"""
    GDPR = "gdpr"
    CCPA = "ccpa"
    HIPAA = "hipaa"
    SOX = "sox"
    ISO27001 = "iso27001"


class DataCategory(Enum):
    """Categories of personal data"""
    PERSONAL_IDENTIFIABLE = "pii"
    FINANCIAL = "financial"
    HEALTH = "health"
    BEHAVIORAL = "behavioral"
    BIOMETRIC = "biometric"
    LOCATION = "location"


class AccessLevel(Enum):
    """Access levels for role-based access control"""
    READ_ONLY = "read"
    READ_WRITE = "write"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


@dataclass
class DataProcessingRecord:
    """Record of data processing activity"""
    record_id: str
    user_id: str
    data_category: DataCategory
    processing_purpose: str
    data_subject: str
    processing_time: datetime
    retention_period: Optional[int] = None  # days
    legal_basis: Optional[str] = None
    data_source: Optional[str] = None
    third_parties: List[str] = None


@dataclass
class AuditLogEntry:
    """Enhanced audit log entry"""
    id: str
    timestamp: datetime
    user_id: str
    username: str
    action: str
    resource_type: str
    resource_id: str
    ip_address: str
    user_agent: str
    session_id: str
    success: bool
    details: Dict[str, Any]
    risk_level: str = "low"  # low, medium, high, critical


@dataclass
class ComplianceViolation:
    """Compliance violation record"""
    violation_id: str
    timestamp: datetime
    standard: ComplianceStandard
    violation_type: str
    description: str
    severity: str  # low, medium, high, critical
    affected_data: List[str]
    user_id: str
    resolved: bool = False
    resolution_notes: Optional[str] = None


class EnterpriseSecurityManager:
    """Enterprise security and compliance manager"""
    
    def __init__(self, database_path: str = "data/enterprise.db"):
        self.logger = logging.getLogger(__name__)
        self.db_path = database_path
        self.lock = threading.Lock()
        
        # Create database directory
        os.makedirs(os.path.dirname(database_path), exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Compliance settings
        self.compliance_standards = {
            ComplianceStandard.GDPR: {
                "max_retention_days": 2555,  # 7 years
                "consent_required": True,
                "data_portability": True,
                "right_to_deletion": True
            },
            ComplianceStandard.CCPA: {
                "max_retention_days": 1825,  # 5 years
                "consent_required": True,
                "data_portability": True,
                "right_to_deletion": True
            }
        }
        
        # Risk assessment thresholds
        self.risk_thresholds = {
            "failed_login_attempts": 5,
            "suspicious_activity_window": 300,  # 5 minutes
            "high_privilege_actions": ["delete_profile", "export_data", "admin_access"]
        }
        
        # Active compliance monitoring
        self.violation_callbacks: List[Callable] = []
        
    def _init_database(self):
        """Initialize enterprise security database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Audit logs table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        username TEXT NOT NULL,
                        action TEXT NOT NULL,
                        resource_type TEXT NOT NULL,
                        resource_id TEXT NOT NULL,
                        ip_address TEXT NOT NULL,
                        user_agent TEXT,
                        session_id TEXT,
                        success BOOLEAN NOT NULL,
                        details TEXT,
                        risk_level TEXT DEFAULT 'low',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Data processing records table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS data_processing_records (
                        record_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        data_category TEXT NOT NULL,
                        processing_purpose TEXT NOT NULL,
                        data_subject TEXT NOT NULL,
                        processing_time TEXT NOT NULL,
                        retention_period INTEGER,
                        legal_basis TEXT,
                        data_source TEXT,
                        third_parties TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Compliance violations table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS compliance_violations (
                        violation_id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        standard TEXT NOT NULL,
                        violation_type TEXT NOT NULL,
                        description TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        affected_data TEXT,
                        user_id TEXT NOT NULL,
                        resolved BOOLEAN DEFAULT FALSE,
                        resolution_notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # User sessions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        username TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        last_activity TEXT NOT NULL,
                        ip_address TEXT NOT NULL,
                        user_agent TEXT,
                        active BOOLEAN DEFAULT TRUE
                    )
                """)
                
                # Data retention policies table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS retention_policies (
                        policy_id TEXT PRIMARY KEY,
                        data_category TEXT NOT NULL,
                        retention_days INTEGER NOT NULL,
                        compliance_standard TEXT NOT NULL,
                        auto_delete BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
                self.logger.info("Enterprise security database initialized")
                
        except Exception as e:
            self.logger.error(f"Database initialization error: {e}")
            raise
    
    def log_audit_event(self, 
                       user_id: str,
                       username: str,
                       action: str,
                       resource_type: str,
                       resource_id: str,
                       ip_address: str,
                       success: bool,
                       details: Dict[str, Any] = None,
                       user_agent: str = None,
                       session_id: str = None) -> str:
        """Log an audit event with enterprise compliance features"""
        
        audit_id = str(uuid.uuid4())
        risk_level = self._assess_risk_level(action, details)
        
        audit_entry = AuditLogEntry(
            id=audit_id,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            username=username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent or "unknown",
            session_id=session_id,
            success=success,
            details=details or {},
            risk_level=risk_level
        )
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO audit_logs 
                    (id, timestamp, user_id, username, action, resource_type, 
                     resource_id, ip_address, user_agent, session_id, success, 
                     details, risk_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    audit_entry.id,
                    audit_entry.timestamp.isoformat(),
                    audit_entry.user_id,
                    audit_entry.username,
                    audit_entry.action,
                    audit_entry.resource_type,
                    audit_entry.resource_id,
                    audit_entry.ip_address,
                    audit_entry.user_agent,
                    audit_entry.session_id,
                    audit_entry.success,
                    json.dumps(audit_entry.details),
                    audit_entry.risk_level
                ))
                conn.commit()
            
            # Check for compliance violations
            self._check_compliance_violations(audit_entry)
            
            # Alert on high-risk activities
            if risk_level in ["high", "critical"]:
                self._handle_high_risk_activity(audit_entry)
            
            return audit_id
            
        except Exception as e:
            self.logger.error(f"Audit logging error: {e}")
            return ""
    
    def _assess_risk_level(self, action: str, details: Dict[str, Any] = None) -> str:
        """Assess risk level of an action"""
        high_risk_actions = [
            "admin_login", "data_export", "profile_delete", "encryption_key_access",
            "security_settings_change", "user_role_change", "bulk_data_download"
        ]
        
        medium_risk_actions = [
            "profile_create", "profile_share", "cloud_sync", "password_change",
            "api_key_generate"
        ]
        
        if action in high_risk_actions:
            return "high"
        elif action in medium_risk_actions:
            return "medium"
        else:
            return "low"
    
    def record_data_processing(self,
                             user_id: str,
                             data_category: DataCategory,
                             processing_purpose: str,
                             data_subject: str,
                             legal_basis: str = None,
                             retention_days: int = None) -> str:
        """Record data processing activity for compliance"""
        
        record_id = str(uuid.uuid4())
        
        record = DataProcessingRecord(
            record_id=record_id,
            user_id=user_id,
            data_category=data_category,
            processing_purpose=processing_purpose,
            data_subject=data_subject,
            processing_time=datetime.utcnow(),
            retention_period=retention_days,
            legal_basis=legal_basis
        )
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO data_processing_records 
                    (record_id, user_id, data_category, processing_purpose, 
                     data_subject, processing_time, retention_period, legal_basis)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.record_id,
                    record.user_id,
                    record.data_category.value,
                    record.processing_purpose,
                    record.data_subject,
                    record.processing_time.isoformat(),
                    record.retention_period,
                    record.legal_basis
                ))
                conn.commit()
            
            return record_id
            
        except Exception as e:
            self.logger.error(f"Data processing record error: {e}")
            return ""
    
    def generate_compliance_report(self,
                                 standard: ComplianceStandard,
                                 start_date: datetime = None,
                                 end_date: datetime = None) -> Dict[str, Any]:
        """Generate compliance report for specified standard"""
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get audit logs in date range
                cursor.execute("""
                    SELECT COUNT(*) as total_events,
                           SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_events,
                           SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END) as high_risk_events
                    FROM audit_logs
                    WHERE timestamp BETWEEN ? AND ?
                """, (start_date.isoformat(), end_date.isoformat()))
                
                audit_stats = cursor.fetchone()
                
                # Get data processing records
                cursor.execute("""
                    SELECT data_category, COUNT(*) as count
                    FROM data_processing_records
                    WHERE processing_time BETWEEN ? AND ?
                    GROUP BY data_category
                """, (start_date.isoformat(), end_date.isoformat()))
                
                processing_stats = dict(cursor.fetchall())
                
                # Get compliance violations
                cursor.execute("""
                    SELECT severity, COUNT(*) as count
                    FROM compliance_violations
                    WHERE timestamp BETWEEN ? AND ? AND standard = ?
                    GROUP BY severity
                """, (start_date.isoformat(), end_date.isoformat(), standard.value))
                
                violation_stats = dict(cursor.fetchall())
                
                # Generate report
                report = {
                    "report_id": str(uuid.uuid4()),
                    "standard": standard.value,
                    "reporting_period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    },
                    "audit_summary": {
                        "total_events": audit_stats[0] if audit_stats else 0,
                        "successful_events": audit_stats[1] if audit_stats else 0,
                        "high_risk_events": audit_stats[2] if audit_stats else 0
                    },
                    "data_processing": processing_stats,
                    "violations": violation_stats,
                    "compliance_status": self._assess_compliance_status(standard, violation_stats),
                    "recommendations": self._generate_compliance_recommendations(standard, violation_stats),
                    "generated_at": datetime.utcnow().isoformat()
                }
                
                return report
                
        except Exception as e:
            self.logger.error(f"Compliance report generation error: {e}")
            return {}
    
    def _assess_compliance_status(self, 
                                standard: ComplianceStandard, 
                                violations: Dict[str, int]) -> str:
        """Assess overall compliance status"""
        critical_violations = violations.get("critical", 0)
        high_violations = violations.get("high", 0)
        
        if critical_violations > 0:
            return "non_compliant"
        elif high_violations > 5:
            return "at_risk"
        elif high_violations > 0:
            return "needs_attention"
        else:
            return "compliant"
    
    def _generate_compliance_recommendations(self,
                                           standard: ComplianceStandard,
                                           violations: Dict[str, int]) -> List[str]:
        """Generate compliance recommendations"""
        recommendations = []
        
        if violations.get("critical", 0) > 0:
            recommendations.append("Immediately address critical compliance violations")
        
        if violations.get("high", 0) > 0:
            recommendations.append("Review and remediate high-severity violations")
        
        if standard == ComplianceStandard.GDPR:
            recommendations.extend([
                "Ensure all data processing has legal basis documented",
                "Implement data retention policies",
                "Provide data portability mechanisms"
            ])
        
        return recommendations
    
    def handle_data_subject_request(self,
                                  request_type: str,
                                  data_subject: str,
                                  requester_email: str) -> Dict[str, Any]:
        """Handle data subject requests (GDPR Article 15-22)"""
        
        request_id = str(uuid.uuid4())
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if request_type == "access":
                    # Right to access (Article 15)
                    cursor.execute("""
                        SELECT * FROM data_processing_records
                        WHERE data_subject = ?
                    """, (data_subject,))
                    
                    records = cursor.fetchall()
                    
                    return {
                        "request_id": request_id,
                        "request_type": "access",
                        "data_subject": data_subject,
                        "processing_records": len(records),
                        "data_categories": list(set(record[2] for record in records)),
                        "status": "completed"
                    }
                
                elif request_type == "deletion":
                    # Right to erasure (Article 17)
                    cursor.execute("""
                        DELETE FROM data_processing_records
                        WHERE data_subject = ?
                    """, (data_subject,))
                    
                    deleted_records = cursor.rowcount
                    conn.commit()
                    
                    return {
                        "request_id": request_id,
                        "request_type": "deletion",
                        "data_subject": data_subject,
                        "deleted_records": deleted_records,
                        "status": "completed"
                    }
                
                elif request_type == "portability":
                    # Right to data portability (Article 20)
                    cursor.execute("""
                        SELECT * FROM data_processing_records
                        WHERE data_subject = ?
                    """, (data_subject,))
                    
                    records = cursor.fetchall()
                    
                    # Create portable data package
                    portable_data = {
                        "data_subject": data_subject,
                        "export_date": datetime.utcnow().isoformat(),
                        "records": [dict(zip([col[0] for col in cursor.description], record)) 
                                  for record in records]
                    }
                    
                    return {
                        "request_id": request_id,
                        "request_type": "portability",
                        "data_subject": data_subject,
                        "portable_data": portable_data,
                        "status": "completed"
                    }
                
        except Exception as e:
            self.logger.error(f"Data subject request error: {e}")
            return {
                "request_id": request_id,
                "status": "error",
                "error": str(e)
            }
    
    def _check_compliance_violations(self, audit_entry: AuditLogEntry):
        """Check for potential compliance violations"""
        violations = []
        
        # Check for excessive failed login attempts
        if audit_entry.action == "login" and not audit_entry.success:
            recent_failures = self._count_recent_failed_logins(
                audit_entry.user_id, 
                minutes=15
            )
            
            if recent_failures > 5:
                violations.append({
                    "type": "excessive_failed_logins",
                    "severity": "medium",
                    "description": f"User {audit_entry.username} has {recent_failures} failed login attempts"
                })
        
        # Check for suspicious data access patterns
        if audit_entry.action in ["profile_access", "data_export"]:
            if self._detect_suspicious_access_pattern(audit_entry):
                violations.append({
                    "type": "suspicious_data_access",
                    "severity": "high",
                    "description": "Unusual data access pattern detected"
                })
        
        # Record violations
        for violation in violations:
            self._record_compliance_violation(
                violation["type"],
                violation["severity"],
                violation["description"],
                audit_entry.user_id
            )
    
    def _record_compliance_violation(self,
                                   violation_type: str,
                                   severity: str,
                                   description: str,
                                   user_id: str):
        """Record a compliance violation"""
        
        violation_id = str(uuid.uuid4())
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO compliance_violations
                    (violation_id, timestamp, standard, violation_type, 
                     description, severity, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    violation_id,
                    datetime.utcnow().isoformat(),
                    "general",
                    violation_type,
                    description,
                    severity,
                    user_id
                ))
                conn.commit()
            
            # Notify violation callbacks
            for callback in self.violation_callbacks:
                try:
                    callback(violation_type, severity, description, user_id)
                except Exception as e:
                    self.logger.error(f"Violation callback error: {e}")
                    
        except Exception as e:
            self.logger.error(f"Violation recording error: {e}")
    
    def _count_recent_failed_logins(self, user_id: str, minutes: int = 15) -> int:
        """Count recent failed login attempts"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM audit_logs
                    WHERE user_id = ? AND action = 'login' 
                    AND success = 0 AND timestamp > ?
                """, (user_id, cutoff_time.isoformat()))
                
                return cursor.fetchone()[0]
                
        except Exception as e:
            self.logger.error(f"Failed login count error: {e}")
            return 0
    
    def _detect_suspicious_access_pattern(self, audit_entry: AuditLogEntry) -> bool:
        """Detect suspicious data access patterns"""
        # Implement pattern detection logic
        # This is a simplified example
        try:
            # Check for rapid consecutive accesses
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cutoff_time = datetime.utcnow() - timedelta(minutes=5)
                
                cursor.execute("""
                    SELECT COUNT(*) FROM audit_logs
                    WHERE user_id = ? AND action IN ('profile_access', 'data_export')
                    AND timestamp > ?
                """, (audit_entry.user_id, cutoff_time.isoformat()))
                
                recent_accesses = cursor.fetchone()[0]
                return recent_accesses > 10  # Threshold for suspicious activity
                
        except Exception as e:
            self.logger.error(f"Suspicious pattern detection error: {e}")
            return False
    
    def _handle_high_risk_activity(self, audit_entry: AuditLogEntry):
        """Handle high-risk security activities"""
        self.logger.warning(f"High-risk activity detected: {audit_entry.action} by {audit_entry.username}")
        
        # Could trigger additional security measures:
        # - Send security alerts
        # - Require additional authentication
        # - Temporarily restrict access
        # - Log to external SIEM system
    
    def add_violation_callback(self, callback: Callable):
        """Add callback for compliance violations"""
        self.violation_callbacks.append(callback)
    
    def get_audit_logs(self,
                      start_date: datetime = None,
                      end_date: datetime = None,
                      user_id: str = None,
                      action: str = None,
                      limit: int = 1000) -> List[Dict[str, Any]]:
        """Retrieve audit logs with filtering"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM audit_logs WHERE 1=1"
                params = []
                
                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(start_date.isoformat())
                
                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(end_date.isoformat())
                
                if user_id:
                    query += " AND user_id = ?"
                    params.append(user_id)
                
                if action:
                    query += " AND action = ?"
                    params.append(action)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                # Convert to dictionaries
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Audit log retrieval error: {e}")
            return []