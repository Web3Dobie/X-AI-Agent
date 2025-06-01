"""
Notion logging utility for recording tweets and headline vault entries.
Uses centralized config.py values for all env vars.
"""

import logging
import os

from notion_client import Client
from .config import LOG_DIR, NOTION_API_KEY, NOTION_TWEET_LOG_DB, HEADLINE_VAULT_DB_ID

# Ensure log directory
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, "notion_logger.log")

# Dedicated logger
logger = logging.getLogger("notion_logger")
logger.setLevel(logging.DEBUG)
if not any(isinstance(h, logging.FileHandler) and h.baseFilename == log_file
           for h in logger.handlers):
    fh = logging.FileHandler(log_file)
    fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(fh)

# Initialize Notion client
notion = Client(auth=NOTION_API_KEY)


def log_to_notion(tweet_id, date, tweet_type, url, likes, retweets, replies, engagement_score):
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


def log_headline(date_ingested, headline, relevance_score, viral_score, used, source_url):
    """
    Append a headline entry to the Notion headline vault database.
    """
    logger.debug(
        f"[Notion] Payload for headline vault: db={HEADLINE_VAULT_DB_ID}, "
        f"headline={headline!r}, date={date_ingested}, rel={relevance_score}, "
        f"viral={viral_score}, used={used}, url={source_url!r}"
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
