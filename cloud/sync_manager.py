"""
Secure cloud synchronization service for form data and profiles.
Supports end-to-end encryption and real-time collaboration features.
"""

import asyncio
import json
import logging
import hashlib
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import aiofiles
import websockets
import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os


@dataclass
class SyncProfile:
    """Encrypted profile for cloud synchronization"""
    profile_id: str
    name: str
    encrypted_data: str
    checksum: str
    last_modified: datetime
    version: int
    owner_id: str
    shared_with: List[str]
    
    
@dataclass
class SyncConflict:
    """Represents a synchronization conflict"""
    profile_id: str
    local_version: int
    remote_version: int
    local_data: Dict[str, Any]
    remote_data: Dict[str, Any]
    conflict_timestamp: datetime


@dataclass
class CollaborationSession:
    """Real-time collaboration session"""
    session_id: str
    profile_id: str
    participants: List[str]
    created_at: datetime
    last_activity: datetime
    is_active: bool


class CloudSyncManager:
    """Manages secure cloud synchronization of form data"""
    
    def __init__(self, 
                 api_base_url: str,
                 api_key: str,
                 encryption_key: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.api_base_url = api_base_url.rstrip('/')
        self.api_key = api_key
        self.user_id: Optional[str] = None
        
        # Initialize encryption
        if encryption_key:
            self.fernet = Fernet(encryption_key.encode())
        else:
            self._generate_encryption_key()
        
        # Sync state
        self.sync_enabled = True
        self.auto_sync_interval = 300  # 5 minutes
        self.last_sync_time = 0
        self.sync_callbacks: List[Callable] = []
        
        # Conflict resolution strategy
        self.conflict_resolution = 'manual'  # 'manual', 'local_wins', 'remote_wins', 'merge'
        
        # WebSocket for real-time features
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.collaboration_enabled = False
        
        # Session management
        self.session_token: Optional[str] = None
        self.session_expires: Optional[datetime] = None
    
    def _generate_encryption_key(self):
        """Generate a new encryption key from user password"""
        # In production, this should derive from user password
        key = Fernet.generate_key()
        self.fernet = Fernet(key)
        
        # Store key securely (this is simplified)
        key_file = os.path.expanduser("~/.formfiller/sync_key")
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        with open(key_file, 'wb') as f:
            f.write(key)
    
    async def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with cloud service"""
        try:
            response = requests.post(
                f"{self.api_base_url}/auth/login",
                json={
                    "username": username,
                    "password": password
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                auth_data = response.json()
                self.session_token = auth_data.get('token')
                self.user_id = auth_data.get('user_id')
                
                # Parse expiration
                expires_str = auth_data.get('expires')
                if expires_str:
                    self.session_expires = datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
                
                self.logger.info(f"Authentication successful for user: {username}")
                return True
            else:
                self.logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        if self.session_token:
            headers["X-Session-Token"] = self.session_token
        
        return headers
    
    async def sync_profile(self, profile_id: str, profile_data: Dict[str, Any]) -> bool:
        """Sync a single profile with cloud"""
        if not self.sync_enabled or not self.user_id:
            return False
        
        try:
            # Encrypt profile data
            encrypted_data = self._encrypt_profile_data(profile_data)
            
            # Calculate checksum
            checksum = self._calculate_checksum(encrypted_data)
            
            # Create sync profile
            sync_profile = SyncProfile(
                profile_id=profile_id,
                name=profile_data.get('name', 'Unnamed Profile'),
                encrypted_data=encrypted_data,
                checksum=checksum,
                last_modified=datetime.now(timezone.utc),
                version=profile_data.get('version', 1),
                owner_id=self.user_id,
                shared_with=profile_data.get('shared_with', [])
            )
            
            # Upload to cloud
            response = requests.put(
                f"{self.api_base_url}/profiles/{profile_id}",
                json=asdict(sync_profile),
                headers=self._get_auth_headers(),
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                self.logger.info(f"Profile {profile_id} synced successfully")
                self._notify_sync_callbacks('profile_synced', profile_id)
                return True
            else:
                self.logger.error(f"Profile sync failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Profile sync error: {e}")
            return False
    
    async def download_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Download and decrypt a profile from cloud"""
        if not self.user_id:
            return None
        
        try:
            response = requests.get(
                f"{self.api_base_url}/profiles/{profile_id}",
                headers=self._get_auth_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                sync_profile_data = response.json()
                sync_profile = SyncProfile(**sync_profile_data)
                
                # Verify checksum
                if not self._verify_checksum(sync_profile.encrypted_data, sync_profile.checksum):
                    self.logger.error(f"Checksum verification failed for profile {profile_id}")
                    return None
                
                # Decrypt profile data
                decrypted_data = self._decrypt_profile_data(sync_profile.encrypted_data)
                
                # Add metadata
                decrypted_data.update({
                    'profile_id': sync_profile.profile_id,
                    'last_modified': sync_profile.last_modified,
                    'version': sync_profile.version,
                    'shared_with': sync_profile.shared_with
                })
                
                return decrypted_data
            
            elif response.status_code == 404:
                self.logger.info(f"Profile {profile_id} not found in cloud")
                return None
            else:
                self.logger.error(f"Profile download failed: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Profile download error: {e}")
            return None
    
    async def sync_all_profiles(self, local_profiles: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Sync all local profiles with cloud"""
        results = {
            'synced': [],
            'conflicts': [],
            'errors': [],
            'downloaded': []
        }
        
        if not self.sync_enabled or not self.user_id:
            return results
        
        try:
            # Get list of cloud profiles
            response = requests.get(
                f"{self.api_base_url}/profiles",
                headers=self._get_auth_headers(),
                timeout=30
            )
            
            if response.status_code != 200:
                self.logger.error(f"Failed to get cloud profiles: {response.status_code}")
                return results
            
            cloud_profiles = response.json()
            cloud_profile_ids = {p['profile_id'] for p in cloud_profiles}
            
            # Sync local profiles to cloud
            for profile_id, profile_data in local_profiles.items():
                success = await self.sync_profile(profile_id, profile_data)
                if success:
                    results['synced'].append(profile_id)
                else:
                    results['errors'].append(profile_id)
            
            # Download new profiles from cloud
            local_profile_ids = set(local_profiles.keys())
            new_profiles = cloud_profile_ids - local_profile_ids
            
            for profile_id in new_profiles:
                downloaded_profile = await self.download_profile(profile_id)
                if downloaded_profile:
                    results['downloaded'].append({
                        'profile_id': profile_id,
                        'data': downloaded_profile
                    })
            
            # Check for conflicts
            conflicts = await self._detect_conflicts(local_profiles, cloud_profiles)
            results['conflicts'] = conflicts
            
            self.last_sync_time = time.time()
            self._notify_sync_callbacks('sync_completed', results)
            
        except Exception as e:
            self.logger.error(f"Full sync error: {e}")
            results['errors'].append(f"sync_error: {str(e)}")
        
        return results
    
    async def _detect_conflicts(self, 
                               local_profiles: Dict[str, Dict[str, Any]], 
                               cloud_profiles: List[Dict]) -> List[SyncConflict]:
        """Detect synchronization conflicts"""
        conflicts = []
        
        cloud_profile_dict = {p['profile_id']: p for p in cloud_profiles}
        
        for profile_id, local_data in local_profiles.items():
            if profile_id in cloud_profile_dict:
                cloud_profile = cloud_profile_dict[profile_id]
                
                local_version = local_data.get('version', 1)
                remote_version = cloud_profile.get('version', 1)
                
                local_modified = local_data.get('last_modified')
                remote_modified = cloud_profile.get('last_modified')
                
                # Check for version conflicts
                if (local_version != remote_version or
                    (local_modified and remote_modified and 
                     local_modified != remote_modified)):
                    
                    # Download remote data for comparison
                    remote_data = await self.download_profile(profile_id)
                    
                    if remote_data:
                        conflict = SyncConflict(
                            profile_id=profile_id,
                            local_version=local_version,
                            remote_version=remote_version,
                            local_data=local_data,
                            remote_data=remote_data,
                            conflict_timestamp=datetime.now(timezone.utc)
                        )
                        conflicts.append(conflict)
        
        return conflicts
    
    async def resolve_conflict(self, 
                             conflict: SyncConflict, 
                             resolution: str = 'manual') -> Optional[Dict[str, Any]]:
        """Resolve synchronization conflict"""
        if resolution == 'local_wins':
            # Use local version
            await self.sync_profile(conflict.profile_id, conflict.local_data)
            return conflict.local_data
        
        elif resolution == 'remote_wins':
            # Use remote version
            return conflict.remote_data
        
        elif resolution == 'merge':
            # Attempt automatic merge
            merged_data = self._merge_profile_data(conflict.local_data, conflict.remote_data)
            if merged_data:
                await self.sync_profile(conflict.profile_id, merged_data)
                return merged_data
        
        # Manual resolution required
        return None
    
    def _merge_profile_data(self, local_data: Dict[str, Any], remote_data: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to merge conflicting profile data"""
        merged = remote_data.copy()
        
        # Simple merge strategy: prefer non-empty values
        for key, local_value in local_data.items():
            if key not in merged or not merged[key]:
                merged[key] = local_value
            elif local_value and local_value != merged[key]:
                # For conflicting non-empty values, create a combined field
                if isinstance(local_value, str) and isinstance(merged[key], str):
                    merged[f"{key}_local"] = local_value
                    merged[f"{key}_remote"] = merged[key]
        
        # Update version and timestamp
        merged['version'] = max(
            local_data.get('version', 1),
            remote_data.get('version', 1)
        ) + 1
        merged['last_modified'] = datetime.now(timezone.utc)
        merged['merge_timestamp'] = datetime.now(timezone.utc)
        
        return merged
    
    async def share_profile(self, profile_id: str, user_email: str, permissions: str = 'read') -> bool:
        """Share a profile with another user"""
        try:
            response = requests.post(
                f"{self.api_base_url}/profiles/{profile_id}/share",
                json={
                    "user_email": user_email,
                    "permissions": permissions
                },
                headers=self._get_auth_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                self.logger.info(f"Profile {profile_id} shared with {user_email}")
                return True
            else:
                self.logger.error(f"Profile sharing failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Profile sharing error: {e}")
            return False
    
    async def start_collaboration_session(self, profile_id: str) -> Optional[str]:
        """Start real-time collaboration session"""
        if not self.collaboration_enabled:
            return None
        
        try:
            response = requests.post(
                f"{self.api_base_url}/collaboration/sessions",
                json={
                    "profile_id": profile_id,
                    "user_id": self.user_id
                },
                headers=self._get_auth_headers(),
                timeout=30
            )
            
            if response.status_code == 201:
                session_data = response.json()
                session_id = session_data['session_id']
                
                # Connect to WebSocket for real-time updates
                await self._connect_collaboration_websocket(session_id)
                
                return session_id
            
        except Exception as e:
            self.logger.error(f"Collaboration session error: {e}")
        
        return None
    
    async def _connect_collaboration_websocket(self, session_id: str):
        """Connect to collaboration WebSocket"""
        try:
            ws_url = f"{self.api_base_url.replace('http', 'ws')}/collaboration/ws/{session_id}"
            
            self.websocket = await websockets.connect(
                ws_url,
                extra_headers=self._get_auth_headers()
            )
            
            # Start listening for messages
            asyncio.create_task(self._listen_collaboration_messages())
            
        except Exception as e:
            self.logger.error(f"WebSocket connection error: {e}")
    
    async def _listen_collaboration_messages(self):
        """Listen for real-time collaboration messages"""
        if not self.websocket:
            return
        
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self._handle_collaboration_message(data)
        except Exception as e:
            self.logger.error(f"WebSocket message error: {e}")
    
    async def _handle_collaboration_message(self, message: Dict[str, Any]):
        """Handle incoming collaboration message"""
        message_type = message.get('type')
        
        if message_type == 'field_update':
            # Another user updated a field
            self._notify_sync_callbacks('field_updated', message.get('data'))
        
        elif message_type == 'user_joined':
            # User joined collaboration session
            self._notify_sync_callbacks('user_joined', message.get('user'))
        
        elif message_type == 'user_left':
            # User left collaboration session
            self._notify_sync_callbacks('user_left', message.get('user'))
    
    async def send_collaboration_update(self, field_name: str, field_value: str):
        """Send field update to collaboration session"""
        if not self.websocket:
            return
        
        message = {
            "type": "field_update",
            "data": {
                "field_name": field_name,
                "field_value": field_value,
                "user_id": self.user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        try:
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            self.logger.error(f"Failed to send collaboration update: {e}")
    
    def _encrypt_profile_data(self, data: Dict[str, Any]) -> str:
        """Encrypt profile data for cloud storage"""
        json_data = json.dumps(data, default=str)
        encrypted = self.fernet.encrypt(json_data.encode())
        return base64.b64encode(encrypted).decode()
    
    def _decrypt_profile_data(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt profile data from cloud storage"""
        encrypted_bytes = base64.b64decode(encrypted_data.encode())
        decrypted = self.fernet.decrypt(encrypted_bytes)
        return json.loads(decrypted.decode())
    
    def _calculate_checksum(self, data: str) -> str:
        """Calculate SHA-256 checksum for data integrity"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _verify_checksum(self, data: str, expected_checksum: str) -> bool:
        """Verify data integrity using checksum"""
        actual_checksum = self._calculate_checksum(data)
        return actual_checksum == expected_checksum
    
    def add_sync_callback(self, callback: Callable):
        """Add callback for sync events"""
        self.sync_callbacks.append(callback)
    
    def _notify_sync_callbacks(self, event_type: str, data: Any):
        """Notify registered callbacks of sync events"""
        for callback in self.sync_callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                self.logger.error(f"Callback error: {e}")
    
    async def start_auto_sync(self):
        """Start automatic synchronization background task"""
        while self.sync_enabled:
            try:
                # This would be called with actual profile data from the app
                # await self.sync_all_profiles(current_profiles)
                pass
            except Exception as e:
                self.logger.error(f"Auto-sync error: {e}")
            
            await asyncio.sleep(self.auto_sync_interval)
    
    def enable_sync(self):
        """Enable cloud synchronization"""
        self.sync_enabled = True
        self.logger.info("Cloud synchronization enabled")
    
    def disable_sync(self):
        """Disable cloud synchronization"""
        self.sync_enabled = False
        self.logger.info("Cloud synchronization disabled")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.websocket:
            await self.websocket.close()
        
        # Logout/invalidate session
        if self.session_token:
            try:
                requests.post(
                    f"{self.api_base_url}/auth/logout",
                    headers=self._get_auth_headers(),
                    timeout=10
                )
            except:
                pass