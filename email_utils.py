import aiosmtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv
load_dotenv()
async def send_email(to_email:str, subject:str, body:str):
    msg = EmailMessage()
    msg['From'] = os.getenv('SMTP_USER')
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.set_content(body)
    try:
        await aiosmtplib.send(
            msg,
            hostname=os.getenv('SMTP_HOST'),
            port=int(os.getenv('SMTP_PORT')),
            username=os.getenv('SMTP_USER'),
            password=os.getenv('SMTP_PASSWORD'),
            start_tls=True
        )
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")