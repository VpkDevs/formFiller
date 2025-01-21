from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

@dataclass
class Event:
    timestamp: datetime = datetime.now()

@dataclass
class ProfileChanged(Event):
    old_profile: str
    new_profile: str

@dataclass
class FormFilled(Event):
    profile: str
    fields_filled: Dict[str, str]
    duration: float
    success: bool
    errors: Optional[Dict[str, str]] = None

@dataclass
class SecurityEvent(Event):
    operation: str
    success: bool
    details: Optional[str] = None

class EventBus:
    def __init__(self):
        self._handlers = {}
        
    def subscribe(self, event_type: type, handler: callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        
    def publish(self, event: Event):
        handlers = self._handlers.get(type(event), [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logging.error(f"Error handling event {type(event)}: {e}")