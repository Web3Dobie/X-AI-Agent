# utils/substack.py - FIXED with proper logging

import os
import logging
from datetime import datetime
from pathlib import Path
import re
import smtplib
from email.message import EmailMessage

# Configure logging for this module
logger = logging.getLogger(__name__)

def send_article_email(title, filename, summary, recipients=None):
    """Send article email with enhanced error handling and logging"""
    user = os.getenv("SMTP_USER")
    app_password = os.getenv("SMTP_PASS")
    
    if not user or not app_password:
        logger.error("❌ SMTP_USER or SMTP_PASS not set in environment!")
        return False

    if recipients is None:
        recipients = os.getenv("ALERT_RECIPIENT") or user

    # Always ensure recipients is a list
    if isinstance(recipients, str):
        recipients = [r.strip() for r in recipients.split(",")]

    try:
        msg = EmailMessage()
        msg["Subject"] = f"New Substack Article: {title}"
        msg["From"] = user
        msg["To"] = ", ".join(recipients)
        msg.set_content(summary or "See attached markdown article.")

        # Attach the file
        if os.path.exists(filename):
            with open(filename, "rb") as f:
                md_data = f.read()
            msg.add_attachment(md_data, maintype="text", subtype="markdown", filename=os.path.basename(filename))
        else:
            logger.error(f"❌ Article file not found: {filename}")
            return False

        # Send the email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(user, app_password)
            smtp.send_message(msg)
        
        logger.info(f"✅ Sent email to: {recipients} with attachment: {filename}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send article email: {e}")
        return False

# Where to store all posts (set this to your actual content directory)
POST_ROOT_DIR = os.getenv("SUBSTACK_POST_DIR", "./posts")

def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    return re.sub(r"\W+", "-", text.lower()).strip("-")

def save_article(content: str, title: str, article_type: str = "article", extension: str = "md") -> str:
    """
    Save the article content to disk and return the file path.
    Enhanced with better error handling and logging.
    """
    try:
        date_str = datetime.now().strftime("%Y-%m-%d")
        safe_title = slugify(title)
        dir_path = os.path.join(POST_ROOT_DIR, article_type)
        
        # Ensure directory exists
        os.makedirs(dir_path, exist_ok=True)
        
        filename = f"{date_str}_{safe_title}.{extension}"
        filepath = os.path.join(dir_path, filename)
        
        # Write the file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"✅ Saved article '{title}' to {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"❌ Failed to save article '{title}': {e}")
        raise

def generate_substack_article(
    content: str,
    title: str,
    article_type: str = "article",
    tags: list = None,
    summary: str = None,
    extension: str = "md",
    notify_email: bool = False,
    email_recipients: list = None
) -> str:
    """
    Orchestrates saving, logging, and optional notification for a new article.
    Enhanced with better error handling.
    """
    try:
        # Save the article
        filepath = save_article(content, title, article_type, extension)
        
        # Log to Notion (import here to avoid circular imports)
        try:
            from .notion_logger import log_substack_post_to_notion
            log_substack_post_to_notion(
                title=title,
                filename=filepath,
                tags=tags,
                category=article_type,
                summary=summary,
            )
            logger.debug(f"✅ Logged article to Notion: {title}")
        except ImportError:
            logger.warning("⚠️ Notion logging not available (missing notion_logger module)")
        except Exception as e:
            logger.error(f"❌ Failed to log article to Notion: {e}")
        
        # Send email notification if requested
        if notify_email:
            email_success = send_article_email(title, filepath, summary, recipients=email_recipients)
            if not email_success:
                logger.warning(f"⚠️ Email notification failed for article: {title}")
        
        return filepath
        
    except Exception as e:
        logger.error(f"❌ Failed to generate Substack article '{title}': {e}")
        raise

# For direct script testing
if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Example test usage
    try:
        example_md = "# Test Article\n\nThis is a test article."
        fname = generate_substack_article(
            example_md,
            title="Test Article",
            article_type="macro",
            tags=["macro", "example"],
            summary="A test macro article.",
            notify_email=False,  # Set to False for testing
            email_recipients=None
        )
        logger.info(f"✅ Test article generated: {fname}")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")