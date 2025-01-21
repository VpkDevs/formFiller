import tkinter as tk
from tkinter import ttk, messagebox
import json
import pyautogui
import keyboard
import time
import os
import logging
from datetime import datetime
import re

class FormAutofiller:
    def __init__(self, root):
        self.root = root
        self.root.title("Form Autofiller Pro")
        self.root.geometry("800x800")
        
        # Setup logging
        self.setup_logging()
        
        # Configuration
        self.config = {
            "field_delay": 0.2,  # Delay between fields
            "key_delay": 0.05,   # Delay between keystrokes
            "retry_attempts": 3,  # Number of retry attempts for failed fields
            "hotkey": "ctrl+space"
        }
        
        # Load or create default profiles
        self.profiles_dir = "profiles"
        os.makedirs(self.profiles_dir, exist_ok=True)
        self.current_profile = "default"
        self.load_profile()
        
        self.create_gui()
        self.setup_hotkey()
        
        # Initialize custom field mappings
        self.custom_mappings = self.load_custom_mappings()
    
    def setup_logging(self):
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"autofiller_{datetime.now().strftime('%Y%m%d')}.log")
        
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def load_custom_mappings(self):
        mappings_file = "field_mappings.json"
        if os.path.exists(mappings_file):
            with open(mappings_file, 'r') as f:
                return json.load(f)
        return {}
    
    def load_profile(self):
        profile_path = os.path.join(self.profiles_dir, f"{self.current_profile}.json")
        if os.path.exists(profile_path):
            with open(profile_path, 'r') as f:
                self.profile = json.load(f)
        else:
            self.profile = {
                "personal": {
                    "first_name": "Vincent",
                    "last_name": "Kinney",
                    "email": "vincekinney1991@gmail.com",
                    "phone": "210-274-2163",
                    "address": "11800 Braesview",
                    "address line 2": "Apt 2505",
                    "city": "San Antonio",
                    "state": "Texas",
                    "zip": "78213",
                    "ssn": "643-22-4250",
                    "dob": "01.09.1991 (09.01.1991)",
                    "company": "",
                    "job_title": "",
                    "website": "",
                    "linkedin": "",
                    "github": "",
                    "country": "",
                    "nationality": "",
                    "gender": "",
                    "marital_status": "",
                    "driver_license": "",
                    "passport": "",
                    "emergency_contact": "",
                    "blood_type": "",
                    "education": "",
                    "skills": "",
                    "languages": "",
                    "bio": "",
                    "twitter": "",
                    "facebook": "",
                    "instagram": "",
                    "preferred_name": "",
                    "middle_name": "",
                    "suffix": "",
                    "title": ""
                },
                "payment": {
                    "card_number": "",
                    "card_name": "",
                    "expiry_date": "",
                    "cvv": "",
                    "billing_address": "",
                    "billing_city": "",
                    "billing_state": "",
                    "billing_zip": "",
                    "billing_country": ""
                },
                "preferences": {
                    "newsletter": True,
                    "marketing_emails": False,
                    "dark_mode": False,
                    "language": "English"
                }
            }
    
    def save_profile(self):
        profile_path = os.path.join(self.profiles_dir, f"{self.current_profile}.json")
        with open(profile_path, 'w') as f:
            json.dump(self.profile, f, indent=4)
        self.logger.info(f"Profile '{self.current_profile}' saved successfully")
        self.show_status("Profile saved successfully!")
    
    def validate_field(self, field_type, value):
        """Validate field values based on their type"""
        validations = {
            'email': lambda x: re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', x) is not None,
            'phone': lambda x: re.match(r'^\+?1?\d{9,15}$', x) is not None,
            'zip': lambda x: re.match(r'^\d{5}(-\d{4})?$', x) is not None,
            'ssn': lambda x: re.match(r'^\d{3}-\d{2}-\d{4}$', x) is not None,
            'dob': lambda x: re.match(r'^\d{2}/\d{2}/\d{4}$', x) is not None
        }
        
        if field_type in validations:
            return validations[field_type](value)
        return True
    
    def create_gui(self):
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create tabs
        self.personal_tab = self.create_scrollable_frame("Personal Information")
        self.payment_tab = self.create_scrollable_frame("Payment Information")
        self.preferences_tab = self.create_scrollable_frame("Preferences")
        self.settings_tab = self.create_scrollable_frame("Settings")
        
        # Add tabs to notebook
        self.notebook.add(self.personal_tab, text="Personal")
        self.notebook.add(self.payment_tab, text="Payment")
        self.notebook.add(self.preferences_tab, text="Preferences")
        self.notebook.add(self.settings_tab, text="Settings")
        
        # Create entry fields for each tab
        self.create_personal_fields()
        self.create_payment_fields()
        self.create_preference_fields()
        self.create_settings_fields()
        
        # Profile management
        profile_frame = ttk.Frame(self.root)
        profile_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(profile_frame, text="Profile:").pack(side='left')
        self.profile_var = tk.StringVar(value=self.current_profile)
        self.profile_entry = ttk.Entry(profile_frame, textvariable=self.profile_var)
        self.profile_entry.pack(side='left', padx=5)
        
        ttk.Button(profile_frame, text="Load", command=self.load_profile_by_name).pack(side='left')
        ttk.Button(profile_frame, text="Save", command=self.save_current_profile).pack(side='left', padx=5)
        ttk.Button(profile_frame, text="New", command=self.new_profile).pack(side='left')
        
        # Status Bar
        self.status_var = tk.StringVar()
        ttk.Label(self.root, textvariable=self.status_var).pack(pady=5)
    
    def create_scrollable_frame(self, title):
        frame = ttk.Frame(self.notebook)
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        return scrollable_frame
    
    def create_personal_fields(self):
        self.entries = {}
        row = 0
        for field in self.profile["personal"].keys():
            self.create_labeled_entry(self.personal_tab, field, "personal", row)
            row += 1
    
    def create_payment_fields(self):
        row = 0
        for field in self.profile["payment"].keys():
            self.create_labeled_entry(self.payment_tab, field, "payment", row)
            row += 1
    
    def create_preference_fields(self):
        row = 0
        for field, value in self.profile["preferences"].items():
            if isinstance(value, bool):
                var = tk.BooleanVar(value=value)
                ttk.Label(self.preferences_tab, text=field.replace("_", " ").title()).grid(row=row, column=0, sticky=tk.W, pady=2, padx=5)
                chk = ttk.Checkbutton(self.preferences_tab, variable=var)
                chk.grid(row=row, column=1, sticky=tk.W, pady=2, padx=5)
                self.entries[f"preferences.{field}"] = var
            else:
                self.create_labeled_entry(self.preferences_tab, field, "preferences", row)
            row += 1
    
    def create_settings_fields(self):
        row = 0
        # Field delay setting
        ttk.Label(self.settings_tab, text="Field Delay (seconds)").grid(row=row, column=0, sticky=tk.W, pady=2, padx=5)
        self.field_delay_var = tk.StringVar(value=str(self.config["field_delay"]))
        ttk.Entry(self.settings_tab, textvariable=self.field_delay_var).grid(row=row, column=1, sticky=tk.W, pady=2, padx=5)
        
        row += 1
        # Key delay setting
        ttk.Label(self.settings_tab, text="Key Delay (seconds)").grid(row=row, column=0, sticky=tk.W, pady=2, padx=5)
        self.key_delay_var = tk.StringVar(value=str(self.config["key_delay"]))
        ttk.Entry(self.settings_tab, textvariable=self.key_delay_var).grid(row=row, column=1, sticky=tk.W, pady=2, padx=5)
        
        row += 1
        # Hotkey setting
        ttk.Label(self.settings_tab, text="Hotkey").grid(row=row, column=0, sticky=tk.W, pady=2, padx=5)
        self.hotkey_var = tk.StringVar(value=self.config["hotkey"])
        ttk.Entry(self.settings_tab, textvariable=self.hotkey_var).grid(row=row, column=1, sticky=tk.W, pady=2, padx=5)
        
        row += 1
        # Save settings button
        ttk.Button(self.settings_tab, text="Save Settings", command=self.save_settings).grid(row=row, column=0, columnspan=2, pady=20)
    
    def create_labeled_entry(self, parent, field, section, row):
        label_text = field.replace("_", " ").title()
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky=tk.W, pady=2, padx=5)
        
        entry = ttk.Entry(parent, width=40)
        entry.grid(row=row, column=1, sticky=tk.W, pady=2, padx=5)
        entry.insert(0, self.profile[section][field])
        self.entries[f"{section}.{field}"] = entry
    
    def setup_hotkey(self):
        try:
            keyboard.add_hotkey(self.config["hotkey"], self.autofill_form)
            self.logger.info(f"Hotkey {self.config['hotkey']} registered successfully")
        except Exception as e:
            self.logger.error(f"Failed to register hotkey: {str(e)}")
            messagebox.showerror("Error", f"Failed to register hotkey: {str(e)}")
    
    def save_settings(self):
        try:
            self.config["field_delay"] = float(self.field_delay_var.get())
            self.config["key_delay"] = float(self.key_delay_var.get())
            new_hotkey = self.hotkey_var.get()
            
            if new_hotkey != self.config["hotkey"]:
                keyboard.remove_hotkey(self.config["hotkey"])
                self.config["hotkey"] = new_hotkey
                self.setup_hotkey()
            
            with open("config.json", 'w') as f:
                json.dump(self.config, f, indent=4)
            
            self.show_status("Settings saved successfully!")
            self.logger.info("Settings saved successfully")
        except Exception as e:
            self.logger.error(f"Failed to save settings: {str(e)}")
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
    
    def load_profile_by_name(self):
        self.current_profile = self.profile_var.get()
        self.load_profile()
        self.refresh_gui()
        self.show_status(f"Profile '{self.current_profile}' loaded")
    
    def new_profile(self):
        self.current_profile = self.profile_var.get()
        self.profile = {
            "personal": {field: "" for field in self.profile["personal"]},
            "payment": {field: "" for field in self.profile["payment"]},
            "preferences": {field: False if isinstance(value, bool) else "" 
                          for field, value in self.profile["preferences"].items()}
        }
        self.refresh_gui()
        self.show_status(f"New profile '{self.current_profile}' created")
    
    def refresh_gui(self):
        for section in ["personal", "payment"]:
            for field in self.profile[section]:
                entry = self.entries.get(f"{section}.{field}")
                if entry:
                    entry.delete(0, tk.END)
                    entry.insert(0, self.profile[section][field])
        
        for field, value in self.profile["preferences"].items():
            entry = self.entries.get(f"preferences.{field}")
            if entry:
                if isinstance(value, bool):
                    entry.set(value)
                else:
                    entry.delete(0, tk.END)
                    entry.insert(0, value)
    
    def save_current_profile(self):
        try:
            # Validate and save personal information
            for field in self.profile["personal"]:
                value = self.entries[f"personal.{field}"].get()
                if not self.validate_field(field, value):
                    raise ValueError(f"Invalid {field} format")
                self.profile["personal"][field] = value
            
            # Save payment information
            for field in self.profile["payment"]:
                self.profile["payment"][field] = self.entries[f"payment.{field}"].get()
            
            # Save preferences
            for field in self.profile["preferences"]:
                entry = self.entries[f"preferences.{field}"]
                if isinstance(entry, tk.BooleanVar):
                    self.profile["preferences"][field] = entry.get()
                else:
                    self.profile["preferences"][field] = entry.get()
            
            self.save_profile()
            self.logger.info(f"Profile '{self.current_profile}' saved successfully")
        except Exception as e:
            self.logger.error(f"Failed to save profile: {str(e)}")
            messagebox.showerror("Error", f"Failed to save profile: {str(e)}")
    
    def autofill_form(self):
        """Smart form filling function with enhanced field detection and error handling"""
        self.logger.info("Starting form autofill")
        self.show_status("Auto-filling form...")
        time.sleep(0.2)  # Small delay to release hotkey
        
        # Enhanced field variations
        field_variations = {
            'first_name': ['first', 'firstname', 'fname', 'givenname', 'given', 'first-name', 'first_name'],
            'last_name': ['last', 'lastname', 'lname', 'surname', 'familyname', 'last-name', 'last_name', 'family'],
            'email': ['email', 'e-mail', 'emailaddress', 'mail', 'email_address', 'e_mail'],
            'phone': ['phone', 'telephone', 'mobile', 'cell', 'phonenumber', 'phone_number', 'tel'],
            'address': ['address', 'street', 'streetaddress', 'addr', 'address1', 'street_address'],
            'city': ['city', 'town', 'municipality'],
            'state': ['state', 'province', 'region', 'county'],
            'zip': ['zip', 'zipcode', 'postal', 'postalcode', 'zip_code', 'postal_code'],
            'ssn': ['ssn', 'social', 'socialsecurity', 'social_security'],
            'dob': ['dob', 'birthdate', 'dateofbirth', 'birth', 'birth_date', 'date_of_birth'],
            'company': ['company', 'organization', 'employer', 'business', 'company_name'],
            'job_title': ['job', 'title', 'position', 'jobtitle', 'job_title', 'role'],
            'website': ['website', 'site', 'webpage', 'url', 'web', 'homepage'],
            'linkedin': ['linkedin', 'linkedinurl', 'linkedin_url'],
            'github': ['github', 'githuburl', 'github_url', 'git'],
            'country': ['country', 'nation', 'country_name'],
            'nationality': ['nationality', 'citizenship'],
            'gender': ['gender', 'sex'],
            'marital_status': ['marital', 'marital_status', 'marriage'],
            'driver_license': ['driver', 'license', 'driver_license', 'drivers_license'],
            'passport': ['passport', 'passport_number'],
            'emergency_contact': ['emergency', 'emergency_contact', 'ice'],
            'blood_type': ['blood', 'blood_type', 'bloodtype'],
            'education': ['education', 'degree', 'qualification'],
            'skills': ['skills', 'expertise', 'competencies'],
            'languages': ['languages', 'spoken_languages'],
            'bio': ['bio', 'about', 'description', 'summary'],
            'twitter': ['twitter', 'twitter_url', 'twitter_handle'],
            'facebook': ['facebook', 'facebook_url', 'fb'],
            'instagram': ['instagram', 'instagram_url', 'ig'],
            'preferred_name': ['preferred', 'nickname', 'preferred_name'],
            'middle_name': ['middle', 'middlename', 'middle_name'],
            'suffix': ['suffix', 'name_suffix'],
            'title': ['title', 'name_title', 'prefix']
        }

        # Add custom mappings
        field_variations.update(self.custom_mappings)
        
        def try_fill_field(field_type, value, attempt=0):
            if not value or attempt >= self.config["retry_attempts"]:
                return
            
            try:
                pyautogui.write(value, interval=self.config["key_delay"])
                time.sleep(self.config["field_delay"])
                pyautogui.press('tab')
                self.logger.debug(f"Filled field {field_type} with value {value}")
            except Exception as e:
                self.logger.error(f"Error filling field {field_type}: {str(e)}")
                if attempt < self.config["retry_attempts"]:
                    time.sleep(self.config["field_delay"] * 2)
                    try_fill_field(field_type, value, attempt + 1)
        
        # Try to fill each field
        for field_type, variations in field_variations.items():
            section = "personal" if field_type in self.profile["personal"] else "payment"
            if section == "payment" and field_type not in self.profile["payment"]:
                continue
                
            value = self.profile[section].get(field_type, "")
            if value:
                try_fill_field(field_type, value)
        
        self.show_status("Form filled!")
        self.logger.info("Form autofill completed")
    
    def show_status(self, message):
        self.status_var.set(message)
        self.root.after(3000, lambda: self.status_var.set(""))

def main():
    try:
        root = tk.Tk()
        app = FormAutofiller(root)
        root.mainloop()
    except Exception as e:
        logging.error(f"Application error: {str(e)}")
        messagebox.showerror("Error", f"Application error: {str(e)}")

if __name__ == "__main__":
    main()
