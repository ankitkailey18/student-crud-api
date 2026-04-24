import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def send_email(to_email: str, subject: str, body: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {os.getenv('RESEND_API_KEY')}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": "EduManager <noreply@edumanager.me>",
                    "to": [to_email],
                    "subject": subject,
                    "html": body.replace('\n', '<br>')
                },
                timeout=10
            )
            if response.status_code == 200:
                print(f"Email sent to {to_email}")
            else:
                print(f"Failed to send email: {response.text}")
    except Exception as e:
        print(f"Failed to send email: {e}")