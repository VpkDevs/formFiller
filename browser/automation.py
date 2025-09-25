"""
Multi-browser automation engine supporting Chrome, Firefox, Safari, and Edge.
Provides WebDriver-based form interaction with intelligent field detection.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import json
import re


@dataclass
class BrowserFormField:
    """Represents a form field found in browser"""
    element_id: str
    element_name: str
    element_type: str
    tag_name: str
    placeholder: str
    label: str
    value: str
    is_visible: bool
    is_enabled: bool
    xpath: str
    css_selector: str


@dataclass
class FormAnalysisResult:
    """Result of form analysis in browser"""
    url: str
    form_count: int
    fields: List[BrowserFormField]
    form_metadata: Dict[str, Any]
    page_title: str
    analysis_timestamp: float


class BrowserAutomation:
    """Multi-browser automation for form filling"""
    
    def __init__(self, 
                 browser: str = 'chrome', 
                 headless: bool = False,
                 implicit_wait: int = 10):
        self.logger = logging.getLogger(__name__)
        self.browser_type = browser.lower()
        self.headless = headless
        self.implicit_wait = implicit_wait
        self.driver: Optional[webdriver] = None
        
        # Field detection strategies
        self.field_selectors = {
            'input_fields': [
                'input[type="text"]',
                'input[type="email"]',
                'input[type="password"]',
                'input[type="tel"]',
                'input[type="number"]',
                'input[type="date"]',
                'input[type="url"]',
                'input:not([type])',  # Default type is text
            ],
            'textarea_fields': ['textarea'],
            'select_fields': ['select'],
            'checkbox_fields': ['input[type="checkbox"]'],
            'radio_fields': ['input[type="radio"]'],
            'all_inputs': ['input', 'textarea', 'select']
        }
        
        # Common field identification patterns
        self.field_patterns = {
            'name': ['name', 'fullname', 'full_name', 'user_name', 'username'],
            'first_name': ['fname', 'first_name', 'firstname', 'given_name'],
            'last_name': ['lname', 'last_name', 'lastname', 'surname', 'family_name'],
            'email': ['email', 'e_mail', 'mail', 'email_address'],
            'phone': ['phone', 'telephone', 'mobile', 'cell', 'phone_number'],
            'address': ['address', 'street', 'addr', 'street_address'],
            'city': ['city', 'town', 'locality'],
            'state': ['state', 'province', 'region'],
            'zip': ['zip', 'zipcode', 'postal_code', 'postcode'],
            'country': ['country', 'nation'],
            'company': ['company', 'organization', 'employer'],
            'title': ['title', 'job_title', 'position']
        }
    
    def start_browser(self, **options) -> webdriver:
        """Start the specified browser with options"""
        self.logger.info(f"Starting {self.browser_type} browser")
        
        try:
            if self.browser_type == 'chrome':
                self.driver = self._start_chrome(**options)
            elif self.browser_type == 'firefox':
                self.driver = self._start_firefox(**options)
            elif self.browser_type == 'edge':
                self.driver = self._start_edge(**options)
            else:
                raise ValueError(f"Unsupported browser: {self.browser_type}")
            
            self.driver.implicitly_wait(self.implicit_wait)
            return self.driver
            
        except Exception as e:
            self.logger.error(f"Failed to start browser: {e}")
            raise
    
    def _start_chrome(self, **options) -> webdriver.Chrome:
        """Start Chrome browser with options"""
        chrome_options = ChromeOptions()
        
        if self.headless:
            chrome_options.add_argument('--headless')
        
        # Default options for better automation
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Apply custom options
        for key, value in options.items():
            if key == 'window_size':
                chrome_options.add_argument(f'--window-size={value}')
            elif key == 'user_agent':
                chrome_options.add_argument(f'--user-agent={value}')
        
        return webdriver.Chrome(
            service=webdriver.chrome.service.Service(ChromeDriverManager().install()),
            options=chrome_options
        )
    
    def _start_firefox(self, **options) -> webdriver.Firefox:
        """Start Firefox browser with options"""
        firefox_options = FirefoxOptions()
        
        if self.headless:
            firefox_options.add_argument('--headless')
        
        # Apply custom options
        for key, value in options.items():
            if key == 'window_size':
                width, height = value.split(',')
                firefox_options.add_argument(f'--width={width}')
                firefox_options.add_argument(f'--height={height}')
        
        return webdriver.Firefox(
            service=webdriver.firefox.service.Service(GeckoDriverManager().install()),
            options=firefox_options
        )
    
    def _start_edge(self, **options) -> webdriver.Edge:
        """Start Edge browser with options"""
        edge_options = EdgeOptions()
        
        if self.headless:
            edge_options.add_argument('--headless')
        
        # Default options
        edge_options.add_argument('--no-sandbox')
        edge_options.add_argument('--disable-dev-shm-usage')
        
        return webdriver.Edge(
            service=webdriver.edge.service.Service(EdgeChromiumDriverManager().install()),
            options=edge_options
        )
    
    def navigate_to(self, url: str) -> None:
        """Navigate to a URL"""
        if not self.driver:
            raise RuntimeError("Browser not started. Call start_browser() first.")
        
        self.logger.info(f"Navigating to: {url}")
        self.driver.get(url)
        
        # Wait for page to load
        WebDriverWait(self.driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    
    def analyze_page_forms(self) -> FormAnalysisResult:
        """Analyze all forms on the current page"""
        if not self.driver:
            raise RuntimeError("Browser not started")
        
        current_url = self.driver.current_url
        page_title = self.driver.title
        
        # Find all forms
        forms = self.driver.find_elements(By.TAG_NAME, 'form')
        
        all_fields = []
        form_metadata = {
            'forms_found': len(forms),
            'form_details': []
        }
        
        # Analyze each form
        for i, form in enumerate(forms):
            form_info = self._analyze_form(form, i)
            form_metadata['form_details'].append(form_info['metadata'])
            all_fields.extend(form_info['fields'])
        
        # Also find standalone fields (not inside forms)
        standalone_fields = self._find_standalone_fields()
        all_fields.extend(standalone_fields)
        
        return FormAnalysisResult(
            url=current_url,
            form_count=len(forms),
            fields=all_fields,
            form_metadata=form_metadata,
            page_title=page_title,
            analysis_timestamp=time.time()
        )
    
    def _analyze_form(self, form_element, form_index: int) -> Dict[str, Any]:
        """Analyze a specific form element"""
        form_fields = []
        
        # Get form attributes
        form_action = form_element.get_attribute('action')
        form_method = form_element.get_attribute('method')
        form_name = form_element.get_attribute('name')
        form_id = form_element.get_attribute('id')
        
        # Find all input elements within the form
        for selector_category, selectors in self.field_selectors.items():
            for selector in selectors:
                try:
                    elements = form_element.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        field = self._create_field_object(element)
                        if field:
                            form_fields.append(field)
                except Exception as e:
                    self.logger.debug(f"Error finding elements with selector {selector}: {e}")
        
        form_metadata = {
            'index': form_index,
            'action': form_action,
            'method': form_method,
            'name': form_name,
            'id': form_id,
            'field_count': len(form_fields)
        }
        
        return {
            'fields': form_fields,
            'metadata': form_metadata
        }
    
    def _find_standalone_fields(self) -> List[BrowserFormField]:
        """Find input fields not within a form element"""
        standalone_fields = []
        
        # Find all input elements on the page
        all_inputs = self.driver.find_elements(By.CSS_SELECTOR, 
                                             ', '.join(self.field_selectors['all_inputs']))
        
        for input_element in all_inputs:
            try:
                # Check if element is inside a form
                parent_form = input_element.find_element(By.XPATH, './ancestor::form')
                # If we found a parent form, skip this element (already processed)
                continue
            except NoSuchElementException:
                # Element is not inside a form, so it's standalone
                field = self._create_field_object(input_element)
                if field:
                    standalone_fields.append(field)
        
        return standalone_fields
    
    def _create_field_object(self, element) -> Optional[BrowserFormField]:
        """Create a BrowserFormField object from a web element"""
        try:
            # Get element attributes
            element_id = element.get_attribute('id') or ''
            element_name = element.get_attribute('name') or ''
            element_type = element.get_attribute('type') or ''
            tag_name = element.tag_name.lower()
            placeholder = element.get_attribute('placeholder') or ''
            value = element.get_attribute('value') or ''
            
            # Try to find associated label
            label = self._find_field_label(element)
            
            # Check visibility and enabled status
            is_visible = element.is_displayed()
            is_enabled = element.is_enabled()
            
            # Generate selectors
            xpath = self._generate_xpath(element)
            css_selector = self._generate_css_selector(element)
            
            return BrowserFormField(
                element_id=element_id,
                element_name=element_name,
                element_type=element_type,
                tag_name=tag_name,
                placeholder=placeholder,
                label=label,
                value=value,
                is_visible=is_visible,
                is_enabled=is_enabled,
                xpath=xpath,
                css_selector=css_selector
            )
        
        except Exception as e:
            self.logger.debug(f"Error creating field object: {e}")
            return None
    
    def _find_field_label(self, element) -> str:
        """Find the label associated with a form field"""
        labels = []
        
        # Method 1: Look for label with 'for' attribute matching element id
        element_id = element.get_attribute('id')
        if element_id:
            try:
                label_element = self.driver.find_element(By.CSS_SELECTOR, f'label[for="{element_id}"]')
                labels.append(label_element.text.strip())
            except NoSuchElementException:
                pass
        
        # Method 2: Check if element is inside a label
        try:
            parent_label = element.find_element(By.XPATH, './ancestor::label')
            label_text = parent_label.text.strip()
            # Remove the element's own value from the label text
            element_value = element.get_attribute('value') or ''
            if element_value and element_value in label_text:
                label_text = label_text.replace(element_value, '').strip()
            labels.append(label_text)
        except NoSuchElementException:
            pass
        
        # Method 3: Look for text in preceding elements
        try:
            # Check previous sibling elements
            preceding_elements = element.find_elements(By.XPATH, './preceding-sibling::*')
            for prev_elem in preceding_elements[-3:]:  # Check last 3 siblings
                text = prev_elem.text.strip()
                if text and len(text) < 100:  # Reasonable label length
                    labels.append(text)
        except Exception:
            pass
        
        # Method 4: Check placeholder as potential label
        placeholder = element.get_attribute('placeholder')
        if placeholder:
            labels.append(placeholder)
        
        # Return the best label (longest meaningful text)
        if labels:
            # Filter out empty or very short labels
            meaningful_labels = [l for l in labels if l and len(l) > 1]
            if meaningful_labels:
                # Return the most descriptive label
                return max(meaningful_labels, key=len)
        
        return ""
    
    def _generate_xpath(self, element) -> str:
        """Generate XPath for element"""
        try:
            # Use JavaScript to generate a unique XPath
            xpath = self.driver.execute_script("""
                function getXPath(element) {
                    if (element.id) {
                        return `//*[@id="${element.id}"]`;
                    }
                    if (element === document.body) {
                        return '/html/body';
                    }
                    
                    let ix = 0;
                    let siblings = element.parentNode.childNodes;
                    for (let i = 0; i < siblings.length; i++) {
                        let sibling = siblings[i];
                        if (sibling === element) {
                            return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                        }
                        if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                            ix++;
                        }
                    }
                }
                return getXPath(arguments[0]);
            """, element)
            return xpath or ""
        except Exception:
            return ""
    
    def _generate_css_selector(self, element) -> str:
        """Generate CSS selector for element"""
        try:
            # Start with tag name
            selector_parts = [element.tag_name.lower()]
            
            # Add ID if available
            element_id = element.get_attribute('id')
            if element_id:
                selector_parts.append(f'#{element_id}')
            
            # Add name if available and no ID
            elif element.get_attribute('name'):
                selector_parts.append(f'[name="{element.get_attribute("name")}"]')
            
            # Add type for input elements
            if element.tag_name.lower() == 'input':
                element_type = element.get_attribute('type')
                if element_type:
                    selector_parts.append(f'[type="{element_type}"]')
            
            return ''.join(selector_parts)
        except Exception:
            return ""
    
    def fill_form(self, field_mappings: Dict[str, str], 
                  delay_between_fields: float = 0.5) -> Dict[str, bool]:
        """
        Fill form fields based on field mappings
        
        Args:
            field_mappings: Dict mapping field identifiers to values
            delay_between_fields: Delay between filling fields
        
        Returns:
            Dict indicating success/failure for each field
        """
        results = {}
        
        if not self.driver:
            raise RuntimeError("Browser not started")
        
        # Analyze current page
        form_analysis = self.analyze_page_forms()
        
        # Match fields with provided mappings
        for field_identifier, value in field_mappings.items():
            success = False
            
            # Find matching field
            matching_fields = self._find_matching_fields(field_identifier, form_analysis.fields)
            
            for field in matching_fields:
                try:
                    success = self._fill_field(field, value)
                    if success:
                        break
                except Exception as e:
                    self.logger.warning(f"Failed to fill field {field_identifier}: {e}")
            
            results[field_identifier] = success
            
            if delay_between_fields > 0:
                time.sleep(delay_between_fields)
        
        return results
    
    def _find_matching_fields(self, identifier: str, fields: List[BrowserFormField]) -> List[BrowserFormField]:
        """Find fields matching the identifier"""
        matching_fields = []
        identifier_lower = identifier.lower()
        
        # Direct matches
        for field in fields:
            if (field.element_id.lower() == identifier_lower or
                field.element_name.lower() == identifier_lower or
                field.label.lower() == identifier_lower):
                matching_fields.append(field)
        
        # Pattern-based matches
        if not matching_fields:
            for pattern_type, patterns in self.field_patterns.items():
                if identifier_lower in patterns:
                    for field in fields:
                        field_text = f"{field.element_id} {field.element_name} {field.label} {field.placeholder}".lower()
                        for pattern in patterns:
                            if pattern in field_text:
                                matching_fields.append(field)
                                break
        
        # Fuzzy matches
        if not matching_fields:
            for field in fields:
                field_text = f"{field.element_id} {field.element_name} {field.label} {field.placeholder}".lower()
                if identifier_lower in field_text or any(part in field_text for part in identifier_lower.split('_')):
                    matching_fields.append(field)
        
        return matching_fields
    
    def _fill_field(self, field: BrowserFormField, value: str) -> bool:
        """Fill a specific field with a value"""
        try:
            # Find the element
            element = None
            
            # Try different strategies to find the element
            strategies = [
                (By.ID, field.element_id),
                (By.NAME, field.element_name),
                (By.CSS_SELECTOR, field.css_selector),
                (By.XPATH, field.xpath)
            ]
            
            for by, selector in strategies:
                if selector:
                    try:
                        element = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((by, selector))
                        )
                        break
                    except TimeoutException:
                        continue
            
            if not element:
                self.logger.warning(f"Could not find element for field: {field.element_id}")
                return False
            
            # Clear and fill the field based on its type
            if field.tag_name == 'select':
                from selenium.webdriver.support.ui import Select
                select = Select(element)
                # Try to select by visible text first, then by value
                try:
                    select.select_by_visible_text(value)
                except:
                    try:
                        select.select_by_value(value)
                    except:
                        # Try partial match
                        for option in select.options:
                            if value.lower() in option.text.lower():
                                option.click()
                                break
            
            elif field.element_type == 'checkbox':
                # Handle checkbox
                if value.lower() in ['true', '1', 'yes', 'checked', 'on']:
                    if not element.is_selected():
                        element.click()
                elif value.lower() in ['false', '0', 'no', 'unchecked', 'off']:
                    if element.is_selected():
                        element.click()
            
            elif field.element_type == 'radio':
                # For radio buttons, just click if value suggests selection
                if value.lower() in ['true', '1', 'yes', 'selected', 'on']:
                    element.click()
            
            else:
                # Text input fields
                element.clear()
                element.send_keys(value)
            
            # Wait a moment for any dynamic updates
            time.sleep(0.1)
            
            self.logger.info(f"Successfully filled field {field.element_id or field.element_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error filling field: {e}")
            return False
    
    def take_screenshot(self, filename: Optional[str] = None) -> str:
        """Take a screenshot of the current page"""
        if not self.driver:
            raise RuntimeError("Browser not started")
        
        if not filename:
            filename = f"screenshot_{int(time.time())}.png"
        
        screenshot_path = self.driver.save_screenshot(filename)
        self.logger.info(f"Screenshot saved: {filename}")
        return filename
    
    def execute_javascript(self, script: str, *args) -> Any:
        """Execute JavaScript in the browser"""
        if not self.driver:
            raise RuntimeError("Browser not started")
        
        return self.driver.execute_script(script, *args)
    
    def wait_for_element(self, selector: str, by: By = By.CSS_SELECTOR, timeout: int = 10):
        """Wait for an element to be present and visible"""
        if not self.driver:
            raise RuntimeError("Browser not started")
        
        return WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located((by, selector))
        )
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.logger.info("Closing browser")
            self.driver.quit()
            self.driver = None
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()