# utils/mailer.py

import os
import smtplib
import mimetypes
from email.message import EmailMessage
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)       # switch to DEBUG so we see more info

# Read SMTP settings from environment
SMTP_HOST       = os.getenv("SMTP_HOST")
SMTP_PORT       = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER       = os.getenv("SMTP_USER")
SMTP_PASS       = os.getenv("SMTP_PASS")
ALERT_RECIPIENT = os.getenv("ALERT_RECIPIENT")

def send_email_alert(subject: str, body: str, attachments: list[str] = None):
    """
    Send a plain-text email with optional file attachments.
    attachments: list of filepaths to attach.
    """
    logger.debug("send_email_alert() called with attachments=%r", attachments)

    if not (SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASS and ALERT_RECIPIENT):
        logger.error(
            "Missing one or more SMTP settings. "
            "HOST=%r, PORT=%r, USER=%r, PASS set? %r, RECIPIENT=%r",
            SMTP_HOST, SMTP_PORT, SMTP_USER,
            bool(SMTP_PASS), ALERT_RECIPIENT
        )
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"]    = SMTP_USER
    msg["To"]      = ALERT_RECIPIENT
    msg.set_content(body)

    # Attach files, if any
    for path in attachments or []:
        try:
            ctype, encoding = mimetypes.guess_type(path)
            if ctype is None or encoding:
                ctype = "application/octet-stream"
            maintype, subtype = ctype.split('/', 1)

            with open(path, 'rb') as f:
                file_data = f.read()

            msg.add_attachment(
                file_data,
                maintype=maintype,
                subtype=subtype,
                filename=os.path.basename(path),
            )
            logger.debug("Attached file %s (ctype=%s)", path, ctype)
        except Exception as e:
            logger.error("Failed to attach %s: %s", path, e)

    try:
        logger.debug("Connecting to SMTP server")
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            logger.debug("Starting TLS")
            server.starttls()
            logger.debug("Logging in as %r", SMTP_USER)
            server.login(SMTP_USER, SMTP_PASS)
            logger.debug("Sending message")
            server.send_message(msg)
            logger.info("Email alert sent: %r", subject)
    except Exception as e:
        logger.error("Failed to send email: %s", e, exc_info=True)
