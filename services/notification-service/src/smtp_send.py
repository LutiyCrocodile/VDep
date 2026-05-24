"""SMTP отправка с поддержкой Yandex (587 STARTTLS и 465 SSL)."""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .config import settings

logger = logging.getLogger(__name__)


def _build_message(to_email: str, subject: str, html_content: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email or settings.smtp_username
    msg["To"] = to_email
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    return msg


def _send_via_ssl(msg: MIMEMultipart, to_email: str) -> None:
    with smtplib.SMTP_SSL(settings.smtp_server, settings.smtp_port, timeout=30) as server:
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)


def _send_via_starttls(msg: MIMEMultipart, to_email: str) -> None:
    with smtplib.SMTP(settings.smtp_server, settings.smtp_port, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)


def send_email_sync(to_email: str, subject: str, html_content: str) -> bool:
    username = (settings.smtp_username or "").strip()
    password = (settings.smtp_password or "").strip()
    if not username or not password:
        logger.info("SMTP not configured, skip email to %s: %s", to_email, subject)
        return False

    msg = _build_message(to_email, subject, html_content)
    use_ssl = settings.smtp_use_ssl or settings.smtp_port == 465

    try:
        if use_ssl:
            _send_via_ssl(msg, to_email)
        else:
            _send_via_starttls(msg, to_email)
        logger.info("Email sent to %s via %s:%s", to_email, settings.smtp_server, settings.smtp_port)
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error(
            "SMTP auth failed for %s (535 = неверный пароль или нет доступа к «Почта» в "
            "паролях приложений Яндекса): %s",
            to_email,
            e,
        )
        return False
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, e)
        return False
