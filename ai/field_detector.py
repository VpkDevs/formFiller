"""
AI-powered field detection using machine learning for intelligent form recognition.
Implements pattern matching, context analysis, and semantic understanding of form fields.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import numpy as np
from Levenshtein import ratio as levenshtein_ratio


@dataclass
class FieldDetectionResult:
    """Result of AI field detection analysis"""
    field_name: str
    confidence_score: float
    detected_type: str
    suggestions: List[str]
    context_clues: List[str]
    semantic_category: str


class AIFieldDetector:
    """AI-powered field detection system using multiple ML techniques"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Pre-trained field patterns with semantic categories
        self.field_patterns = {
            'personal': {
                'name': ['name', 'full_name', 'fullname', 'user_name', 'username', 'person_name'],
                'first_name': ['first', 'firstname', 'fname', 'givenname', 'given', 'first-name', 'first_name'],
                'last_name': ['last', 'lastname', 'lname', 'surname', 'familyname', 'last-name', 'last_name', 'family'],
                'middle_name': ['middle', 'middlename', 'mname', 'middle_name', 'mid_name'],
                'email': ['email', 'e-mail', 'emailaddress', 'mail', 'email_address', 'e_mail', 'electronic_mail'],
                'phone': ['phone', 'telephone', 'mobile', 'cell', 'phonenumber', 'phone_number', 'tel', 'contact'],
                'address': ['address', 'street', 'streetaddress', 'addr', 'address1', 'street_address', 'home_address'],
                'city': ['city', 'town', 'municipality', 'locality'],
                'state': ['state', 'province', 'region', 'county', 'territory'],
                'zip': ['zip', 'zipcode', 'postal', 'postalcode', 'zip_code', 'postal_code', 'postcode'],
                'country': ['country', 'nation', 'country_name', 'nationality'],
                'dob': ['dob', 'birthdate', 'dateofbirth', 'birth', 'birth_date', 'date_of_birth', 'birthday'],
                'age': ['age', 'years_old', 'age_years'],
                'gender': ['gender', 'sex', 'male_female'],
                'ssn': ['ssn', 'social', 'socialsecurity', 'social_security', 'social_security_number'],
            },
            'professional': {
                'company': ['company', 'organization', 'employer', 'business', 'company_name', 'org'],
                'job_title': ['job', 'title', 'position', 'jobtitle', 'job_title', 'role', 'profession'],
                'department': ['department', 'dept', 'division', 'team'],
                'salary': ['salary', 'income', 'wage', 'compensation', 'pay'],
                'experience': ['experience', 'years_experience', 'work_experience'],
            },
            'financial': {
                'card_number': ['card', 'cardnumber', 'card_number', 'credit_card', 'debit_card', 'cc_number'],
                'cvv': ['cvv', 'cvc', 'security_code', 'card_security_code', 'verification_code'],
                'expiry': ['expiry', 'expiration', 'exp_date', 'expiry_date', 'valid_thru'],
                'bank_account': ['account', 'account_number', 'bank_account', 'routing'],
                'amount': ['amount', 'price', 'cost', 'total', 'sum', 'value'],
            },
            'contact': {
                'website': ['website', 'site', 'webpage', 'url', 'web', 'homepage', 'link'],
                'linkedin': ['linkedin', 'linkedinurl', 'linkedin_url', 'linkedin_profile'],
                'twitter': ['twitter', 'twitter_url', 'twitter_handle', '@'],
                'facebook': ['facebook', 'facebook_url', 'fb'],
                'instagram': ['instagram', 'instagram_url', 'ig', 'insta'],
            },
            'identity': {
                'passport': ['passport', 'passport_number', 'passport_id'],
                'driver_license': ['driver', 'license', 'driver_license', 'drivers_license', 'dl'],
                'id_number': ['id', 'id_number', 'identification', 'personal_id'],
            }
        }
        
        # Initialize TF-IDF vectorizer for semantic similarity
        self._initialize_vectorizer()
        
        # Context patterns that provide additional clues
        self.context_patterns = {
            'required': ['required', 'mandatory', '*', 'must'],
            'optional': ['optional', 'if_applicable', 'leave_blank'],
            'format_hints': ['format:', 'example:', 'e.g.', 'format', 'pattern'],
            'validation': ['valid', 'invalid', 'error', 'correct'],
        }
    
    def _initialize_vectorizer(self):
        """Initialize TF-IDF vectorizer with field patterns"""
        all_patterns = []
        self.pattern_labels = []
        
        for category, fields in self.field_patterns.items():
            for field_type, patterns in fields.items():
                for pattern in patterns:
                    all_patterns.append(pattern)
                    self.pattern_labels.append(f"{category}.{field_type}")
        
        self.vectorizer = TfidfVectorizer(
            analyzer='char_ngram',
            ngram_range=(2, 4),
            lowercase=True
        )
        
        if all_patterns:
            self.pattern_vectors = self.vectorizer.fit_transform(all_patterns)
    
    def detect_field_type(self, 
                         field_identifier: str, 
                         context_text: str = "", 
                         field_attributes: Dict[str, str] = None) -> FieldDetectionResult:
        """
        Detect field type using AI-powered analysis
        
        Args:
            field_identifier: The field name/id/class identifier
            context_text: Surrounding text context
            field_attributes: HTML attributes or other metadata
        
        Returns:
            FieldDetectionResult with confidence score and suggestions
        """
        field_attributes = field_attributes or {}
        
        # Clean and normalize the field identifier
        normalized_field = self._normalize_field_name(field_identifier)
        
        # Multiple detection strategies
        pattern_score, pattern_match = self._pattern_matching_score(normalized_field)
        semantic_score, semantic_match = self._semantic_similarity_score(normalized_field)
        context_score, context_clues = self._analyze_context(context_text, field_attributes)
        attribute_score, attribute_hints = self._analyze_attributes(field_attributes)
        
        # Combine scores with weighted importance
        final_score = (
            pattern_score * 0.4 +      # Pattern matching is most reliable
            semantic_score * 0.3 +     # Semantic similarity helps with variations
            context_score * 0.2 +      # Context provides additional validation
            attribute_score * 0.1      # Attributes give extra hints
        )
        
        # Determine best match
        best_match = pattern_match if pattern_score > semantic_score else semantic_match
        
        # Generate suggestions for alternative matches
        suggestions = self._generate_suggestions(normalized_field, best_match)
        
        # Determine semantic category
        semantic_category = self._get_semantic_category(best_match)
        
        return FieldDetectionResult(
            field_name=best_match,
            confidence_score=final_score,
            detected_type=self._get_field_type(best_match),
            suggestions=suggestions,
            context_clues=context_clues + attribute_hints,
            semantic_category=semantic_category
        )
    
    def _normalize_field_name(self, field_name: str) -> str:
        """Normalize field name for better matching"""
        if not field_name:
            return ""
        
        # Convert to lowercase and replace separators
        normalized = field_name.lower()
        normalized = re.sub(r'[-_\s\.]+', '_', normalized)
        
        # Remove common prefixes/suffixes
        prefixes = ['input_', 'field_', 'form_', 'user_', 'customer_']
        suffixes = ['_input', '_field', '_box', '_text']
        
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
                break
        
        return normalized
    
    def _pattern_matching_score(self, field_name: str) -> Tuple[float, str]:
        """Score based on exact and fuzzy pattern matching"""
        best_score = 0.0
        best_match = "unknown"
        
        for category, fields in self.field_patterns.items():
            for field_type, patterns in fields.items():
                for pattern in patterns:
                    # Exact match gets highest score
                    if field_name == pattern:
                        return 1.0, f"{category}.{field_type}"
                    
                    # Fuzzy matching using Levenshtein ratio
                    fuzzy_score = levenshtein_ratio(field_name, pattern)
                    
                    # Substring matching
                    if pattern in field_name or field_name in pattern:
                        fuzzy_score = max(fuzzy_score, 0.8)
                    
                    # Regex pattern matching for specific cases
                    regex_score = self._regex_pattern_score(field_name, pattern)
                    
                    combined_score = max(fuzzy_score, regex_score)
                    
                    if combined_score > best_score:
                        best_score = combined_score
                        best_match = f"{category}.{field_type}"
        
        return best_score, best_match
    
    def _semantic_similarity_score(self, field_name: str) -> Tuple[float, str]:
        """Score based on semantic similarity using TF-IDF"""
        if not hasattr(self, 'pattern_vectors'):
            return 0.0, "unknown"
        
        try:
            field_vector = self.vectorizer.transform([field_name])
            similarities = cosine_similarity(field_vector, self.pattern_vectors).flatten()
            
            best_idx = np.argmax(similarities)
            best_score = similarities[best_idx]
            best_match = self.pattern_labels[best_idx]
            
            return float(best_score), best_match
        except Exception as e:
            self.logger.warning(f"Semantic similarity calculation failed: {e}")
            return 0.0, "unknown"
    
    def _analyze_context(self, context_text: str, field_attributes: Dict[str, str]) -> Tuple[float, List[str]]:
        """Analyze surrounding context for additional clues"""
        context_clues = []
        score = 0.0
        
        if not context_text:
            return score, context_clues
        
        context_lower = context_text.lower()
        
        # Look for validation patterns
        if re.search(r'email|@', context_lower):
            context_clues.append("email_indicator")
            score += 0.3
        
        if re.search(r'phone|tel|call', context_lower):
            context_clues.append("phone_indicator")
            score += 0.3
        
        if re.search(r'address|street|zip|postal', context_lower):
            context_clues.append("address_indicator")
            score += 0.3
        
        if re.search(r'name|first|last', context_lower):
            context_clues.append("name_indicator")
            score += 0.2
        
        # Check for format hints
        for pattern_type, patterns in self.context_patterns.items():
            for pattern in patterns:
                if pattern in context_lower:
                    context_clues.append(f"{pattern_type}_{pattern}")
                    score += 0.1
        
        return min(score, 1.0), context_clues
    
    def _analyze_attributes(self, attributes: Dict[str, str]) -> Tuple[float, List[str]]:
        """Analyze field attributes for type hints"""
        attribute_hints = []
        score = 0.0
        
        if not attributes:
            return score, attribute_hints
        
        # HTML input type hints
        input_type = attributes.get('type', '').lower()
        if input_type:
            type_mapping = {
                'email': 0.9,
                'tel': 0.9,
                'url': 0.9,
                'date': 0.9,
                'password': 0.9,
                'number': 0.7,
                'text': 0.1,
            }
            
            if input_type in type_mapping:
                score += type_mapping[input_type]
                attribute_hints.append(f"type_{input_type}")
        
        # Pattern attribute for validation
        pattern = attributes.get('pattern', '')
        if pattern:
            attribute_hints.append("has_validation_pattern")
            score += 0.3
        
        # Placeholder text analysis
        placeholder = attributes.get('placeholder', '')
        if placeholder:
            attribute_hints.append("has_placeholder")
            # Recursively analyze placeholder text
            placeholder_score, _ = self._pattern_matching_score(self._normalize_field_name(placeholder))
            score += placeholder_score * 0.5
        
        return min(score, 1.0), attribute_hints
    
    def _regex_pattern_score(self, field_name: str, pattern: str) -> float:
        """Advanced regex-based pattern matching"""
        # Special patterns for complex matching
        special_patterns = {
            'email': r'.*e?mail.*',
            'phone': r'.*(phone|tel|mobile|cell).*',
            'name': r'.*(name|nom).*',
            'address': r'.*(addr|address|street).*',
            'zip': r'.*(zip|postal).*',
            'date': r'.*(date|birth|dob).*',
        }
        
        for field_type, regex_pattern in special_patterns.items():
            if field_type in pattern and re.match(regex_pattern, field_name):
                return 0.7
        
        return 0.0
    
    def _generate_suggestions(self, field_name: str, best_match: str) -> List[str]:
        """Generate alternative field type suggestions"""
        suggestions = []
        
        # Find top 3 similar matches
        scores = []
        for category, fields in self.field_patterns.items():
            for field_type, patterns in fields.items():
                match_key = f"{category}.{field_type}"
                if match_key != best_match:
                    max_pattern_score = max(
                        levenshtein_ratio(field_name, pattern) for pattern in patterns
                    )
                    scores.append((max_pattern_score, match_key))
        
        # Sort by score and take top 3
        scores.sort(reverse=True, key=lambda x: x[0])
        suggestions = [match for score, match in scores[:3] if score > 0.5]
        
        return suggestions
    
    def _get_semantic_category(self, field_match: str) -> str:
        """Extract semantic category from field match"""
        if '.' in field_match:
            return field_match.split('.')[0]
        return 'unknown'
    
    def _get_field_type(self, field_match: str) -> str:
        """Extract field type from field match"""
        if '.' in field_match:
            return field_match.split('.')[1]
        return field_match
    
    def batch_analyze_fields(self, fields_data: List[Dict[str, Any]]) -> List[FieldDetectionResult]:
        """Analyze multiple fields in batch for better context understanding"""
        results = []
        
        # First pass: individual analysis
        individual_results = []
        for field_data in fields_data:
            field_id = field_data.get('id', '')
            context = field_data.get('context', '')
            attributes = field_data.get('attributes', {})
            
            result = self.detect_field_type(field_id, context, attributes)
            individual_results.append(result)
        
        # Second pass: context-aware improvements
        for i, result in enumerate(individual_results):
            improved_result = self._improve_with_context(result, individual_results, i)
            results.append(improved_result)
        
        return results
    
    def _improve_with_context(self, 
                            result: FieldDetectionResult, 
                            all_results: List[FieldDetectionResult], 
                            current_index: int) -> FieldDetectionResult:
        """Improve detection using context from other fields"""
        # Look for common form patterns
        nearby_results = []
        for i in range(max(0, current_index - 2), min(len(all_results), current_index + 3)):
            if i != current_index:
                nearby_results.append(all_results[i])
        
        # Boost confidence if part of recognized patterns
        pattern_boost = self._detect_form_patterns(result, nearby_results)
        
        # Create improved result
        improved_result = FieldDetectionResult(
            field_name=result.field_name,
            confidence_score=min(1.0, result.confidence_score + pattern_boost),
            detected_type=result.detected_type,
            suggestions=result.suggestions,
            context_clues=result.context_clues + (["pattern_boost"] if pattern_boost > 0 else []),
            semantic_category=result.semantic_category
        )
        
        return improved_result
    
    def _detect_form_patterns(self, 
                            current_result: FieldDetectionResult, 
                            nearby_results: List[FieldDetectionResult]) -> float:
        """Detect common form patterns to boost confidence"""
        boost = 0.0
        
        nearby_types = [r.detected_type for r in nearby_results]
        
        # Common personal info patterns
        if current_result.detected_type == 'first_name' and 'last_name' in nearby_types:
            boost += 0.2
        elif current_result.detected_type == 'last_name' and 'first_name' in nearby_types:
            boost += 0.2
        
        # Address patterns
        address_fields = ['address', 'city', 'state', 'zip']
        if current_result.detected_type in address_fields:
            address_count = sum(1 for t in nearby_types if t in address_fields)
            if address_count >= 2:
                boost += 0.15
        
        # Contact patterns
        contact_fields = ['email', 'phone']
        if current_result.detected_type in contact_fields:
            contact_count = sum(1 for t in nearby_types if t in contact_fields)
            if contact_count >= 1:
                boost += 0.1
        
        return boost