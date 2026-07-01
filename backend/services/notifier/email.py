"""
Email notifier — kirim notifikasi via SMTP.
"""
import smtplib
from email.message import EmailMessage
from backend.core.config import settings
from backend.core.logging import get_logger

logger = get_logger(__name__, service="notifier")


class EmailNotifier:
    """Wrapper class for email notification functions."""
    
    @staticmethod
    async def send_message(subject: str, body: str, to_email: str | None = None) -> bool:
        """Kirim email notifikasi via SMTP."""
        if not settings.smtp_user or not settings.smtp_password:
            logger.warning("Email SMTP tidak dikonfigurasi")
            return False
        
        recipient = to_email or settings.smtp_user
        
        try:
            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = settings.smtp_user
            msg['To'] = recipient
            msg.set_content(body)
            
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email terkirim ke {recipient}")
            return True
        except Exception as e:
            logger.error(f"Gagal kirim email: {e}")
            return False
