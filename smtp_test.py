import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# SMTP server configuration (Gmail example)
smtp_server = "smtp.gmail.com"
smtp_port = 587
sender_email = "yashnachugh2004@gmail.com"
sender_password = "uojw mkbi gssd zksd"  # Use App Password if 2FA is enabled
receiver_email = "receiver_email@example.com"

# Create email message
message = MIMEMultipart()
message["From"] = "yashnachugh2004@gmail.com"
message["To"] = "bajajaryan20@gmail.com"
message["Subject"] = "Test Email from Python SMTP"

body = "Hello! This is a test email sent using Python and SMTP."
message.attach(MIMEText(body, "plain"))

# Connect to SMTP server and send email
try:
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()  # Secure connection
    server.login(sender_email, sender_password)
    server.sendmail("yashnachugh2004@gmail.com", "bajajaryan20@gmail.com", message.as_string())
    print("Email sent successfully!")
except Exception as e:
    print(f"Error: {e}")
finally:
    server.quit()
