"""
Helpers for logging Substack posts to a Notion database.
Logs successes and failures to a centralized log file.
"""

import logging
import os
from datetime import datetime

import requests
from dotenv import load_dotenv

from .config import LOG_DIR

# Load environment variables
load_dotenv()

# Configure logging
log_file = os.path.join(LOG_DIR, "notion_helpers.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Notion API setup from env
NOTION_TOKEN = os.getenv("NOTION_API_KEY")
SUBSTACK_DB_ID = os.getenv("NOTION_SUBSTACK_ARCHIVE_DB_ID")
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def log_substack_post_to_notion(headline: str, filename: str) -> bool:
    """
    Create a new page in the Notion database for a Substack post.
    Returns True if logged successfully, False otherwise.
    """
    url = "https://api.notion.com/v1/pages"
    data = {
        "parent": {"database_id": SUBSTACK_DB_ID},
        "properties": {
            "Headline": {"title": [{"text": {"content": headline}}]},
            "Date": {"date": {"start": datetime.utcnow().isoformat()}},
            "File": {"rich_text": [{"text": {"content": filename}}]},
            "Status": {"select": {"name": "Draft"}},
        },
    }
    try:
        response = requests.post(url, headers=NOTION_HEADERS, json=data)
        response.raise_for_status()
        logging.info(f"[OK] Logged '{headline}' to Notion database {SUBSTACK_DB_ID}.")
        return True
    except Exception as e:
        logging.error(
            f"[ERROR] Failed to log to Notion: {e} - Response: {getattr(e, 'response', '')}"
        )
        return False
