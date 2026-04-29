import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .celery_app import celery_app
from .config import settings
import logging

logger = logging.getLogger(__name__)

@celery_app.task
def send_email_notification(user_email: str, subject: str, body: str):
    """
    Send email notification to user
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = settings.smtp_from_email
        msg['To'] = user_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)
        server.quit()

        logger.info(f"Email sent to {user_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False
