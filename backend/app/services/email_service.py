from email.message import EmailMessage
import logging
import smtplib
from typing import Optional

from app.db.database import settings

logger = logging.getLogger("smart_civic.email")


class EmailService:
    def __init__(self):
        pass

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
    ) -> bool:
        if not settings.SMTP_HOST:
            logger.info(
                f"[EmailService] SMTP not configured. Email to '{to_email}' skipped: {subject}"
            )
            return False

        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_FROM
            msg["To"] = to_email
            msg.set_content(body_text)

            if body_html:
                msg.add_alternative(body_html, subtype="html")

            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=5)
            if settings.SMTP_TLS:
                server.starttls()

            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)

            server.send_message(msg)
            server.quit()
            logger.info(f"[EmailService] Email sent successfully to {to_email}")
            return True
        except Exception as exc:
            # Never expose passwords in logs
            logger.warning(
                f"[EmailService] Failed to send email to {to_email}: {exc.__class__.__name__}"
            )
            return False

    def send_complaint_notification(
        self,
        to_email: str,
        title: str,
        message: str,
    ) -> bool:
        subject = f"[Smart Civic System] {title}"
        body_text = f"Hello,\n\n{message}\n\nThank you,\nSmart Civic Response Team"
        return self.send_email(to_email=to_email, subject=subject, body_text=body_text)


email_service = EmailService()
