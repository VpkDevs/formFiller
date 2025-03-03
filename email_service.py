import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_verification_email(to_email: str, otp: str):
    """Send a verification email with the provided OTP."""
    from_email = "your_email@example.com"  # Replace with your email
    password = "your_email_password"  # Replace with your email password

    subject = "Email Verification"
    body = f"Your verification code is: {otp}"

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP('smtp.example.com', 587) as server:  # Replace with your SMTP server
            server.starttls()
            server.login(from_email, password)
            server.send_message(msg)
    except Exception as e:
        print(f"Failed to send email: {e}")
