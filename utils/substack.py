# utils/substack.py

import os
from datetime import datetime
from pathlib import Path
import re
import logging
import smtplib
from email.message import EmailMessage

# If you already have a log_substack_post_to_notion elsewhere, import and extend it here
# Example stub:

def send_article_email(title, filename, summary, recipients=None):
    user = os.getenv("SMTP_USER")
    app_password = os.getenv("SMTP_PASS")
    if not user or not app_password:
        print("❌ GMAIL_USER or GMAIL_APP_PASSWORD not set in environment!")
        return

    if recipients is None:
        recipients = os.getenv("ALERT_RECIPIENT") or user

    # Always ensure recipients is a list
    if isinstance(recipients, str):
        recipients = [r.strip() for r in recipients.split(",")]

    msg = EmailMessage()
    msg["Subject"] = f"New Substack Article: {title}"
    msg["From"] = user
    msg["To"] = ", ".join(recipients)
    msg.set_content(summary or "See attached markdown article.")

    with open(filename, "rb") as f:
        md_data = f.read()
    msg.add_attachment(md_data, maintype="text", subtype="markdown", filename=os.path.basename(filename))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(user, app_password)
        smtp.send_message(msg)
    print(f"✅ Sent email to: {recipients} with attachment: {filename}")

# Where to store all posts (set this to your actual content directory)
POST_ROOT_DIR = os.getenv("SUBSTACK_POST_DIR", "./posts")

def slugify(text: str) -> str:
    return re.sub(r"\W+", "-", text.lower()).strip("-")

def save_article(content: str, title: str, article_type: str = "article", extension: str = "md") -> str:
    """
    Save the article content to disk and return the file path.
    
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_title = slugify(title)
    dir_path = os.path.join(POST_ROOT_DIR, article_type)
    os.makedirs(dir_path, exist_ok=True)
    filename = f"{date_str}_{safe_title}.{extension}"
    filepath = os.path.join(dir_path, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    logging.info(f"Saved article '{title}' to {filepath}")
    return filepath

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
    """
    filepath = save_article(content, title, article_type, extension)
    log_substack_post_to_notion(
        title=title,
        filename=filepath,
        tags=tags,
        category=article_type,
        summary=summary,
    )
    if notify_email:
        send_article_email(title, filepath, summary, recipients=email_recipients)
    return filepath

# For direct script testing
if __name__ == "__main__":
    # Example test usage
    example_md = "# Test Article\n\nThis is a test article."
    fname = generate_substack_article(
        example_md,
        title="Test Article",
        article_type="macro",
        tags=["macro", "example"],
        summary="A test macro article.",
        notify_email=True,
        email_recipients=["your@email.com"]
    )
    print(f"Test article generated: {fname}")
