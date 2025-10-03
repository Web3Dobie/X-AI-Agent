# utils/notion_logger.py (Simplified and Corrected)

import logging
from datetime import datetime
from notion_client import Client
from .config import NOTION_API_KEY, NOTION_TWEET_LOG_DB, NOTION_SUBSTACK_ARCHIVE_DB_ID

logger = logging.getLogger(__name__)
notion = Client(auth=NOTION_API_KEY)

def log_article_to_notion(headline: str, file_url: str, tags: list, category: str, summary: str) -> str:
    """
    Logs an article's metadata to the Notion Articles DB and returns the page ID.
    This replaces the old 'log_substack_post_to_notion' function.
    """
    props = {
        "Headline": {"title": [{"text": {"content": headline}}]},
        "Date":     {"date":  {"start": datetime.utcnow().isoformat()}},
        "File":     {"url": file_url}, # URL to the locally hosted .md file
        "Status":   {"select": {"name": "Published"}},
        "Category": {"select": {"name": category}},
        "Tags":     {"multi_select": [{"name": tag} for tag in tags]},
        "Summary":  {"rich_text": [{"text": {"content": summary}}]}
    }
    try:
        # NOTE: The DB ID is NOTION_SUBSTACK_ARCHIVE_DB_ID from your old file.
        # You may want to rename this variable in your config for clarity (e.g., to NOTION_ARTICLES_DB_ID).
        response = notion.pages.create(
            parent={"database_id": NOTION_SUBSTACK_ARCHIVE_DB_ID},
            properties=props,
        )
        page_id = response["id"]
        logger.info(f"Successfully logged article '{headline}' to Notion. Page ID: {page_id}")
        return page_id
    except Exception as e:
        logger.error(f"Failed to log article '{headline}' to Notion: {e}")
        return None

def update_notion_article_with_tweet_url(page_id: str, tweet_url: str):
    """Updates an existing Notion article page with the announcement tweet URL."""
    if not page_id: return
    try:
        notion.pages.update(page_id=page_id, properties={"Tweet": {"url": tweet_url}})
        logger.info(f"Updated Notion page {page_id} with tweet URL: {tweet_url}")
    except Exception as e:
        logger.error(f"Failed to update Notion page {page_id} with tweet URL: {e}")