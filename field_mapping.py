from dataclasses import dataclass
from typing import List, Dict, Optional
import re

@dataclass
class FieldMapping:
    name: str
    variations: List[str]
    validation_pattern: Optional[str] = None
    transform_function: Optional[callable] = None
    sensitive: bool = False

class FieldMappingRegistry:
    def __init__(self):
        self._mappings: Dict[str, FieldMapping] = {}
        self._variation_index: Dict[str, str] = {}
        
    def register(self, mapping: FieldMapping):
        self._mappings[mapping.name] = mapping
        for variation in mapping.variations:
            self._variation_index[variation.lower()] = mapping.name
            
    def find_mapping(self, field_name: str) -> Optional[FieldMapping]:
        normalized = field_name.lower()
        if normalized in self._variation_index:
            return self._mappings[self._variation_index[normalized]]
        
        # Try fuzzy matching if exact match fails
        return self._fuzzy_match(normalized)
    
    def _fuzzy_match(self, field_name: str) -> Optional[FieldMapping]:
        # Implement fuzzy matching logic using Levenshtein distance
        pass