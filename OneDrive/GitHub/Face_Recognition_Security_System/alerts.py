import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import Optional


class EmailAlertService:
    """
    Optional email alerts configured using environment variables:

    FRS_SMTP_HOST
    FRS_SMTP_PORT
    FRS_SMTP_USER
    FRS_SMTP_PASSWORD
    FRS_ALERT_TO
    FRS_SMTP_USE_TLS=1
    """

    def __init__(self):
        self.host = os.getenv("FRS_SMTP_HOST", "").strip()
        self.port = int(os.getenv("FRS_SMTP_PORT", "587"))
        self.user = os.getenv("FRS_SMTP_USER", "").strip()
        self.password = os.getenv("FRS_SMTP_PASSWORD", "")
        self.recipient = os.getenv("FRS_ALERT_TO", "").strip()
        self.use_tls = os.getenv("FRS_SMTP_USE_TLS", "1") == "1"

    @property
    def configured(self) -> bool:
        return all([self.host, self.user, self.password, self.recipient])

    def send_unknown_alert(self, image_path: str, event_time: str) -> bool:
        if not self.configured:
            return False

        message = EmailMessage()
        message["Subject"] = "Security Alert: Unknown person detected"
        message["From"] = self.user
        message["To"] = self.recipient
        message.set_content(
            f"An unknown person was detected at {event_time}.\n"
            f"Source image: {image_path}"
        )

        path = Path(image_path)
        if path.exists():
            data = path.read_bytes()
            message.add_attachment(
                data,
                maintype="image",
                subtype="jpeg",
                filename=path.name,
            )

        context = ssl.create_default_context()
        with smtplib.SMTP(self.host, self.port, timeout=15) as server:
            if self.use_tls:
                server.starttls(context=context)
            server.login(self.user, self.password)
            server.send_message(message)
        return True
