# notion_logger.py

import logging
import os
import json
from datetime import datetime

import requests
from notion_client import Client
from dotenv import load_dotenv

from .config import (
    LOG_DIR,
    NOTION_API_KEY,
    NOTION_TWEET_LOG_DB,
    HEADLINE_VAULT_DB_ID,
    NOTION_SUBSTACK_ARCHIVE_DB_ID,
)

# ─── Load environment vars ───────────────────────────────────────────────
load_dotenv()
# ────────────────────────────────────────────────────────────────────────

# ─── Ensure log directory exists ────────────────────────────────────────
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, "notion_logger.log")
# ────────────────────────────────────────────────────────────────────────

# ─── Set up a single "notion_logger" ────────────────────────────────────
logger = logging.getLogger("notion_logger")
logger.setLevel(logging.INFO)

# Only add FileHandler if it isn't already attached
if not any(
    isinstance(h, logging.FileHandler) and h.baseFilename == log_file
    for h in logger.handlers
):
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(fh)
# ────────────────────────────────────────────────────────────────────────

# ─── Initialize Notion client ──────────────────────────────────────────
notion = Client(auth=NOTION_API_KEY)
# ────────────────────────────────────────────────────────────────────────


def log_to_notion_tweet(tweet_id, date, tweet_type, url, likes, retweets, replies, engagement_score):
    """
    Append a tweet entry to the Notion tweet log database.
    """
    try:
        notion.pages.create(
            parent={"database_id": NOTION_TWEET_LOG_DB},
            properties={
                "Tweet ID":        {"title":   [{"text": {"content": str(tweet_id)}}]},
                "Date":            {"date":    {"start": date}},
                "Type":            {"select":  {"name": tweet_type}},
                "URL":             {"url":     url},
                "Likes":           {"number":  likes},
                "Retweets":        {"number":  retweets},
                "Replies":         {"number":  replies},
                "Engagement Score":{"number":  engagement_score},
            },
        )
        logger.info(f"[OK] Logged tweet {tweet_id} to Notion DB {NOTION_TWEET_LOG_DB}")
    except Exception as e:
        logger.error(f"[ERROR] Failed to log tweet {tweet_id} to Notion: {e}")


def log_headline_to_vault(date_ingested, headline, relevance_score, viral_score, used, source_url):
    """
    Append a headline entry to the Notion headline vault database.
    """
    logger.debug(
        "[Notion] Preparing payload for headline vault: "
        f"db={HEADLINE_VAULT_DB_ID}, headline={headline!r}, date={date_ingested}, "
        f"rel={relevance_score}, viral={viral_score}, used={used}, url={source_url!r}"
    )

    try:
        notion.pages.create(
            parent={"database_id": HEADLINE_VAULT_DB_ID},
            properties={
                "Headline Vault": {"title":    [{"text": {"content": headline}}]},
                "Date Ingested":  {"date":     {"start": date_ingested}},
                "Relevance Score":{"number":   relevance_score},
                "Viral Score":    {"number":   viral_score},
                "Used?":          {"checkbox": used},
                "Source":         {"url":      source_url},
            },
        )
        logger.info(f"[OK] Logged headline '{headline}' to Notion DB {HEADLINE_VAULT_DB_ID}")
    except Exception as e:
        logger.error(f"[ERROR] Failed to log headline '{headline}' to Notion: {e}")


def log_substack_post_to_notion(
    headline: str,
    blob_url: str,
    tweet_url: str = None,
    tags: list = None,
    category: str = None,
    summary: str = None,
    status: str = "Draft",
) -> str:
    """
    Log a Substack post to Notion and return the page ID.
    
    Returns:
        str: The Notion page ID if successful, None if failed
    """
    props = {
        "Headline": {"title": [{"text": {"content": headline}}]},
        "Date":     {"date":  {"start": datetime.utcnow().isoformat()}},
        "File":     {"url": blob_url},  # URL type property
        "Status":   {"select": {"name": status}},
    }
    if tweet_url:
        props["Tweet"] = {"url": tweet_url}  # Make sure the Notion field is a URL property
    if summary:
        props["Summary"] = {"rich_text": [{"text": {"content": summary}}]}
    if category:
        props["Category"] = {"select": {"name": category}}
    if tags:
        props["Tags"] = {"multi_select": [{"name": tag} for tag in tags]}

    try:
        response = notion.pages.create(
            parent={"database_id": NOTION_SUBSTACK_ARCHIVE_DB_ID},
            properties=props,
        )
        page_id = response["id"]
        logger.info(f"[OK] Logged '{headline}' to Notion DB {NOTION_SUBSTACK_ARCHIVE_DB_ID}, page ID: {page_id}")
        return page_id
    except Exception as e:
        logger.error(f"[ERROR] Couldn't log Substack post '{headline}': {e}")
        return None

def update_notion_page_tweet_url(page_id: str, tweet_url: str) -> bool:
    """
    Update an existing Notion page with a tweet URL.
    
    Args:
        page_id: The Notion page ID
        tweet_url: The tweet URL to add
        
    Returns:
        bool: True if successful, False if failed
    """
    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                "Tweet": {"url": tweet_url}
            }
        )
        logger.info(f"[OK] Updated Notion page {page_id} with tweet URL: {tweet_url}")
        return True
    except Exception as e:
        logger.error(f"[ERROR] Failed to update Notion page {page_id} with tweet URL: {e}")
        return False