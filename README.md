# Form Autofiller Pro

A robust desktop application that automatically fills out forms with intelligent field detection and extensive customization options.

## Enhanced Features

- **Smart Field Detection**
  - Extensive field name variations support
  - Custom field mapping capabilities
  - Intelligent form field recognition

- **Multiple Profile Support**
  - Create and manage multiple profiles
  - Quick profile switching
  - Profile import/export functionality

- **Advanced Form Filling**
  - Configurable delays between fields
  - Adjustable keystroke timing
  - Automatic retry mechanism for failed fields
  - Field validation

- **Comprehensive Data Support**
  - Personal Information
  - Payment Details
  - Preferences
  - Custom Fields

- **Robust Error Handling**
  - Automatic retry for failed fields
  - Detailed error logging
  - User-friendly error messages

- **Customization Options**
  - Configurable hotkeys
  - Adjustable timing settings
  - Custom field mappings

## Available Form Fields

### Personal Information
- First Name
- Last Name
- Middle Name
- Preferred Name
- Title/Suffix
- Email Address
- Phone Number
- Full Address
- City
- State
- ZIP Code
- Country
- Nationality
- Gender
- Marital Status
- Social Security Number
- Driver's License
- Passport Number
- Date of Birth
- Blood Type
- Emergency Contact

### Professional Information
- Company
- Job Title
- Education
- Skills
- Languages
- Bio
- Website

### Social Media
- LinkedIn URL
- GitHub URL
- Twitter
- Facebook
- Instagram

### Payment Information
- Card Number
- Cardholder Name
- Expiry Date
- CVV
- Billing Address
- Billing City
- Billing State
- Billing ZIP
- Billing Country

## Setup Instructions

1. Install Python 3.7 or higher
2. Install required packages:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python main.py
   ```

## Usage

### Basic Usage
1. Launch the application
2. Fill in your information in the appropriate tabs
3. Click "Save Profile" to save your information
4. When filling out forms:
   - Click into the first field of the form
   - Press the configured hotkey (default: Ctrl+Space)
   - The application will automatically fill out all detected fields

### Profile Management
- Create multiple profiles for different purposes
- Switch between profiles using the profile selector
- Export profiles for backup
- Import profiles from other devices

### Settings Customization
1. Open the Settings tab
2. Adjust the following options:
   - Field Delay: Time between filling each field
   - Key Delay: Time between keystrokes
   - Hotkey: Custom keyboard shortcut
3. Click "Save Settings" to apply changes

### Custom Field Mappings
Create custom field mappings in `field_mappings.json`:
```json
{
  "custom_field": ["variation1", "variation2"]
}
```

## Logging and Debugging

- Logs are stored in the `logs` directory
- Each day creates a new log file
- Logs include:
  - Field fill attempts
  - Errors and retries
  - Profile changes
  - Configuration updates

## Data Security

- All data is stored locally
- Profiles are saved in JSON format
- No data is transmitted over the internet
- Sensitive information is stored in plain text - use with caution

## Troubleshooting

If form filling isn't working:
1. Check the logs for error messages
2. Ensure the application has necessary permissions
3. Try adjusting the field and key delays
4. Verify the form fields are focusable
5. Check if custom field mappings are correct
6. Ensure the hotkey isn't conflicting with other applications

Common solutions:
- Increase field delay for slower forms
- Run as administrator for system-wide forms
- Clear and recreate field mappings
- Reset to default settings
- Check for updates to dependencies

## Contributing

Feel free to submit issues and enhancement requests!

## License

MIT License - feel free to use and modify as needed.
