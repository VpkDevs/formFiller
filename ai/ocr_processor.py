"""
OCR (Optical Character Recognition) module for PDF form processing.
Extracts form fields and data from PDF documents using advanced image processing.
"""

import logging
import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import re
import fitz  # PyMuPDF for PDF processing
from pathlib import Path
from io import BytesIO


@dataclass
class OCRFieldResult:
    """Result of OCR field extraction"""
    field_name: str
    field_value: str
    confidence: float
    bounding_box: Tuple[int, int, int, int]  # x, y, width, height
    field_type: str
    page_number: int


@dataclass
class PDFFormField:
    """Represents a detected form field in PDF"""
    label: str
    value: str
    field_type: str  # 'text', 'checkbox', 'signature', etc.
    coordinates: Tuple[float, float, float, float]
    confidence: float
    page: int


class OCRProcessor:
    """Advanced OCR processor for PDF form analysis"""
    
    def __init__(self, tesseract_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # OCR configuration for better accuracy
        self.ocr_config = {
            'default': r'--oem 3 --psm 6',
            'single_line': r'--oem 3 --psm 8',
            'single_word': r'--oem 3 --psm 7',
            'sparse_text': r'--oem 3 --psm 11',
        }
        
        # Field detection patterns
        self.field_patterns = {
            'name_fields': [
                r'name\s*:?',
                r'full\s*name\s*:?',
                r'first\s*name\s*:?',
                r'last\s*name\s*:?',
                r'surname\s*:?',
            ],
            'address_fields': [
                r'address\s*:?',
                r'street\s*:?',
                r'city\s*:?',
                r'state\s*:?',
                r'zip\s*code?\s*:?',
                r'postal\s*code\s*:?',
            ],
            'contact_fields': [
                r'phone\s*:?',
                r'telephone\s*:?',
                r'email\s*:?',
                r'e-?mail\s*:?',
            ],
            'date_fields': [
                r'date\s*:?',
                r'birth\s*date\s*:?',
                r'dob\s*:?',
                r'date\s*of\s*birth\s*:?',
            ],
            'checkbox_patterns': [
                r'☐', r'☑', r'☒', r'□', r'■', r'✓', r'✗',
                r'\[[ x]\]', r'\(\s*[x ]\s*\)',
            ]
        }
    
    def process_pdf(self, pdf_path: str) -> List[PDFFormField]:
        """
        Process a PDF file and extract form fields using OCR
        
        Args:
            pdf_path: Path to the PDF file
        
        Returns:
            List of detected form fields
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        self.logger.info(f"Processing PDF: {pdf_path}")
        
        # Open PDF document
        pdf_document = fitz.open(str(pdf_path))
        all_fields = []
        
        try:
            # Process each page
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                page_fields = self._process_page(page, page_num)
                all_fields.extend(page_fields)
                
        finally:
            pdf_document.close()
        
        self.logger.info(f"Extracted {len(all_fields)} form fields from PDF")
        return all_fields
    
    def _process_page(self, page: fitz.Page, page_num: int) -> List[PDFFormField]:
        """Process a single PDF page"""
        # Convert page to image
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better OCR
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # Convert to PIL Image
        image = Image.open(BytesIO(img_data))
        
        # Preprocess image for better OCR
        processed_image = self._preprocess_image(image)
        
        # Extract text with bounding boxes
        ocr_data = pytesseract.image_to_data(
            processed_image, 
            config=self.ocr_config['default'],
            output_type=pytesseract.Output.DICT
        )
        
        # Detect form fields
        fields = self._detect_form_fields(ocr_data, page_num)
        
        # Enhance field detection with visual analysis
        enhanced_fields = self._enhance_with_visual_analysis(processed_image, fields, page_num)
        
        return enhanced_fields
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR accuracy"""
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Convert PIL to OpenCV
        cv_image = np.array(image)
        
        # Apply noise reduction
        cv_image = cv2.bilateralFilter(cv_image, 9, 75, 75)
        
        # Enhance contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cv_image = clahe.apply(cv_image)
        
        # Apply morphological operations to clean up text
        kernel = np.ones((2, 2), np.uint8)
        cv_image = cv2.morphologyEx(cv_image, cv2.MORPH_CLOSE, kernel)
        
        # Threshold to binary image
        _, cv_image = cv2.threshold(cv_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Convert back to PIL
        processed_image = Image.fromarray(cv_image)
        
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(processed_image)
        processed_image = enhancer.enhance(2.0)
        
        return processed_image
    
    def _detect_form_fields(self, ocr_data: Dict, page_num: int) -> List[PDFFormField]:
        """Detect form fields from OCR data"""
        fields = []
        texts = ocr_data['text']
        confidences = ocr_data['conf']
        left = ocr_data['left']
        top = ocr_data['top']
        width = ocr_data['width']
        height = ocr_data['height']
        
        # Group text by lines for better field detection
        lines = self._group_text_by_lines(ocr_data)
        
        for line_data in lines:
            line_text = ' '.join([text for text in line_data['texts'] if text.strip()])
            
            if not line_text.strip():
                continue
            
            # Detect field labels and values
            field_matches = self._match_field_patterns(line_text)
            
            for match in field_matches:
                field_type = match['type']
                label = match['label']
                value = match['value']
                confidence = match['confidence']
                
                # Calculate bounding box for the field
                bbox = self._calculate_field_bbox(line_data)
                
                field = PDFFormField(
                    label=label,
                    value=value,
                    field_type=field_type,
                    coordinates=bbox,
                    confidence=confidence,
                    page=page_num
                )
                
                fields.append(field)
        
        return fields
    
    def _group_text_by_lines(self, ocr_data: Dict) -> List[Dict]:
        """Group OCR text elements by visual lines"""
        texts = ocr_data['text']
        confidences = ocr_data['conf']
        left = ocr_data['left']
        top = ocr_data['top']
        width = ocr_data['width']
        height = ocr_data['height']
        
        # Create text elements
        elements = []
        for i, text in enumerate(texts):
            if text.strip() and confidences[i] > 30:  # Filter low confidence
                elements.append({
                    'text': text,
                    'left': left[i],
                    'top': top[i],
                    'right': left[i] + width[i],
                    'bottom': top[i] + height[i],
                    'confidence': confidences[i]
                })
        
        # Sort by vertical position
        elements.sort(key=lambda x: x['top'])
        
        # Group into lines based on vertical proximity
        lines = []
        current_line = []
        line_threshold = 10  # pixels
        
        for element in elements:
            if not current_line:
                current_line = [element]
            else:
                # Check if element is on the same line
                avg_top = sum(e['top'] for e in current_line) / len(current_line)
                if abs(element['top'] - avg_top) <= line_threshold:
                    current_line.append(element)
                else:
                    # Start new line
                    if current_line:
                        lines.append(self._create_line_data(current_line))
                    current_line = [element]
        
        # Add the last line
        if current_line:
            lines.append(self._create_line_data(current_line))
        
        return lines
    
    def _create_line_data(self, elements: List[Dict]) -> Dict:
        """Create line data from grouped elements"""
        # Sort elements by horizontal position
        elements.sort(key=lambda x: x['left'])
        
        return {
            'texts': [e['text'] for e in elements],
            'left': min(e['left'] for e in elements),
            'top': min(e['top'] for e in elements),
            'right': max(e['right'] for e in elements),
            'bottom': max(e['bottom'] for e in elements),
            'confidence': sum(e['confidence'] for e in elements) / len(elements),
            'elements': elements
        }
    
    def _match_field_patterns(self, line_text: str) -> List[Dict]:
        """Match text line against known field patterns"""
        matches = []
        line_lower = line_text.lower()
        
        for category, patterns in self.field_patterns.items():
            for pattern in patterns:
                regex_matches = re.finditer(pattern, line_lower)
                
                for regex_match in regex_matches:
                    # Extract label and potential value
                    label_start = regex_match.start()
                    label_end = regex_match.end()
                    
                    label = line_text[label_start:label_end].strip(':').strip()
                    
                    # Look for value after the label
                    remaining_text = line_text[label_end:].strip()
                    value = self._extract_field_value(remaining_text, category)
                    
                    match = {
                        'type': category.replace('_fields', '').replace('_patterns', ''),
                        'label': label,
                        'value': value,
                        'confidence': self._calculate_match_confidence(pattern, line_text),
                        'position': (label_start, label_end)
                    }
                    
                    matches.append(match)
        
        return matches
    
    def _extract_field_value(self, remaining_text: str, field_category: str) -> str:
        """Extract field value based on field category"""
        if not remaining_text:
            return ""
        
        # Remove common separators
        remaining_text = re.sub(r'^[:\-_]+\s*', '', remaining_text)
        
        # Category-specific value extraction
        if field_category == 'date_fields':
            # Look for date patterns
            date_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}'
            match = re.search(date_pattern, remaining_text)
            if match:
                return match.group()
        
        elif field_category == 'contact_fields':
            if 'email' in remaining_text.lower():
                # Extract email pattern
                email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                match = re.search(email_pattern, remaining_text)
                if match:
                    return match.group()
            elif 'phone' in remaining_text.lower():
                # Extract phone pattern
                phone_pattern = r'[\d\-\(\)\s\+]{10,}'
                match = re.search(phone_pattern, remaining_text)
                if match:
                    return match.group().strip()
        
        # Default: extract text until next field or end
        # Look for patterns that indicate start of next field
        next_field_pattern = r'\s+[a-zA-Z]+\s*:'
        match = re.search(next_field_pattern, remaining_text)
        
        if match:
            return remaining_text[:match.start()].strip()
        else:
            # Take first meaningful chunk
            words = remaining_text.split()
            if words:
                # Take up to 5 words or until punctuation
                value_words = []
                for word in words[:5]:
                    if re.match(r'^[a-zA-Z0-9@.\-]+$', word):
                        value_words.append(word)
                    else:
                        break
                return ' '.join(value_words)
        
        return remaining_text.strip()
    
    def _calculate_match_confidence(self, pattern: str, line_text: str) -> float:
        """Calculate confidence score for pattern match"""
        base_confidence = 0.7
        
        # Boost confidence for exact matches
        if pattern.replace(r'\s*:?', '') in line_text.lower():
            base_confidence += 0.2
        
        # Consider context
        context_words = ['form', 'application', 'information', 'details']
        for word in context_words:
            if word in line_text.lower():
                base_confidence += 0.05
        
        return min(base_confidence, 1.0)
    
    def _calculate_field_bbox(self, line_data: Dict) -> Tuple[float, float, float, float]:
        """Calculate bounding box for field"""
        return (
            float(line_data['left']),
            float(line_data['top']),
            float(line_data['right'] - line_data['left']),
            float(line_data['bottom'] - line_data['top'])
        )
    
    def _enhance_with_visual_analysis(self, 
                                    image: Image.Image, 
                                    fields: List[PDFFormField], 
                                    page_num: int) -> List[PDFFormField]:
        """Enhance field detection with visual analysis"""
        cv_image = np.array(image)
        
        # Detect checkboxes and form elements
        checkbox_fields = self._detect_checkboxes(cv_image, page_num)
        
        # Detect input fields/text boxes
        input_fields = self._detect_input_fields(cv_image, page_num)
        
        # Merge all detected fields
        enhanced_fields = fields + checkbox_fields + input_fields
        
        # Remove duplicates and improve positioning
        enhanced_fields = self._deduplicate_fields(enhanced_fields)
        
        return enhanced_fields
    
    def _detect_checkboxes(self, image: np.ndarray, page_num: int) -> List[PDFFormField]:
        """Detect checkboxes using visual analysis"""
        checkboxes = []
        
        # Convert to binary if not already
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Find contours
        contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            # Calculate contour properties
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            
            if area < 100 or area > 2000:  # Filter by reasonable checkbox size
                continue
            
            # Check if contour is roughly square/rectangular
            epsilon = 0.02 * perimeter
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            if len(approx) >= 4:  # Rectangular shape
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h
                
                # Should be roughly square
                if 0.5 <= aspect_ratio <= 2.0:
                    # Check if it's filled (checked)
                    roi = gray[y:y+h, x:x+w]
                    fill_ratio = np.sum(roi < 128) / (w * h)
                    
                    is_checked = fill_ratio > 0.3
                    
                    checkbox = PDFFormField(
                        label="checkbox",
                        value="checked" if is_checked else "unchecked",
                        field_type="checkbox",
                        coordinates=(float(x), float(y), float(w), float(h)),
                        confidence=0.8,
                        page=page_num
                    )
                    
                    checkboxes.append(checkbox)
        
        return checkboxes
    
    def _detect_input_fields(self, image: np.ndarray, page_num: int) -> List[PDFFormField]:
        """Detect input fields/text boxes using visual analysis"""
        input_fields = []
        
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Detect horizontal lines (common in forms)
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        detect_horizontal = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
        
        # Find contours of horizontal lines
        contours, _ = cv2.findContours(detect_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter for line-like shapes (wide and thin)
            if w > 50 and h < 10 and w/h > 5:
                input_field = PDFFormField(
                    label="input_line",
                    value="",
                    field_type="input",
                    coordinates=(float(x), float(y), float(w), float(h)),
                    confidence=0.6,
                    page=page_num
                )
                
                input_fields.append(input_field)
        
        return input_fields
    
    def _deduplicate_fields(self, fields: List[PDFFormField]) -> List[PDFFormField]:
        """Remove duplicate fields based on proximity and similarity"""
        if not fields:
            return fields
        
        unique_fields = []
        processed = set()
        
        for i, field in enumerate(fields):
            if i in processed:
                continue
            
            # Look for duplicates
            duplicates = [field]
            for j, other_field in enumerate(fields[i+1:], i+1):
                if j in processed:
                    continue
                
                # Check if fields are duplicates based on proximity and content
                if self._are_fields_similar(field, other_field):
                    duplicates.append(other_field)
                    processed.add(j)
            
            # Merge duplicates and take the best one
            best_field = self._merge_duplicate_fields(duplicates)
            unique_fields.append(best_field)
            processed.add(i)
        
        return unique_fields
    
    def _are_fields_similar(self, field1: PDFFormField, field2: PDFFormField) -> bool:
        """Check if two fields are similar (likely duplicates)"""
        x1, y1, w1, h1 = field1.coordinates
        x2, y2, w2, h2 = field2.coordinates
        
        # Check proximity
        distance = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
        
        # Check content similarity
        label_similar = field1.label.lower() == field2.label.lower()
        type_similar = field1.field_type == field2.field_type
        
        return distance < 50 and (label_similar or type_similar)
    
    def _merge_duplicate_fields(self, duplicates: List[PDFFormField]) -> PDFFormField:
        """Merge duplicate fields, keeping the best information"""
        if len(duplicates) == 1:
            return duplicates[0]
        
        # Select field with highest confidence
        best_field = max(duplicates, key=lambda f: f.confidence)
        
        # Merge information from other fields
        for field in duplicates:
            if field != best_field:
                # Use better label if available
                if len(field.label) > len(best_field.label) and field.label.strip():
                    best_field = PDFFormField(
                        label=field.label,
                        value=best_field.value or field.value,
                        field_type=best_field.field_type,
                        coordinates=best_field.coordinates,
                        confidence=best_field.confidence,
                        page=best_field.page
                    )
                
                # Use better value if available
                if not best_field.value and field.value:
                    best_field = PDFFormField(
                        label=best_field.label,
                        value=field.value,
                        field_type=best_field.field_type,
                        coordinates=best_field.coordinates,
                        confidence=best_field.confidence,
                        page=best_field.page
                    )
        
        return best_field