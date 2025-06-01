"""
Email sender module for posting Substack articles via email.
Uses SMTP_SSL to send content and logs failures to a centralized log file.
"""

import logging
import os
import smtplib
from email.mime.text import MIMEText

from dotenv import load_dotenv

from .config import LOG_DIR

# Load environment variables
load_dotenv()

# Configure logging
log_file = os.path.join(LOG_DIR, "email_sender.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def post_to_substack_via_email(subject: str, content: str) -> bool:
    """
    Sends the given content as an email to the Substack ingestion address.
    Returns True on success, False on failure.
    """
    sender = os.getenv("EMAIL_USERNAME")
    password = os.getenv("EMAIL_PASSWORD")
    recipient = os.getenv("SUBSTACK_SECRET_EMAIL")

    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, [recipient], msg.as_string())
        logging.info("[OK] Substack article sent via email.")
        return True
    except Exception as e:
        logging.error(f"[ERROR] Failed to send Substack email: {e}")
        return False
