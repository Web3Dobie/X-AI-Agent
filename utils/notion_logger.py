"""
Notion logging utility for recording tweets and headline vault entries.
Uses environment variables for API credentials and database IDs.
Logs success and errors to a centralized log file.
"""

import logging
import os

from dotenv import load_dotenv
from notion_client import Client

from .config import LOG_DIR

# Load environment variables
load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
TWEET_LOG_DB_ID = os.getenv("NOTION_TWEET_LOG_DB")
HEADLINE_VAULT_DB_ID = os.getenv("NOTION_HEADLINE_VAULT_DB_ID")

# Configure logging
log_file = os.path.join(LOG_DIR, "notion_logger.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Initialize Notion client
notion = Client(auth=NOTION_API_KEY)


def log_to_notion(
    tweet_id, date, tweet_type, url, likes, retweets, replies, engagement_score
):
    """
    Append a tweet entry to the Notion tweet log database.
    """
    try:
        notion.pages.create(
            parent={"database_id": TWEET_LOG_DB_ID},
            properties={
                "Tweet ID": {"title": [{"text": {"content": str(tweet_id)}}]},
                "Date": {"date": {"start": date}},
                "Type": {"select": {"name": tweet_type}},
                "URL": {"url": url},
                "Likes": {"number": likes},
                "Retweets": {"number": retweets},
                "Replies": {"number": replies},
                "Engagement Score": {"number": engagement_score},
            },
        )
        logging.info(f"✅ Logged tweet {tweet_id} to Notion DB {TWEET_LOG_DB_ID}")
    except Exception as e:
        logging.error(f"❌ Failed to log tweet {tweet_id} to Notion: {e}")


def log_headline(
    date_ingested, headline, relevance_score, viral_score, used, source_url
):
    """
    Append a headline entry to the Notion headline vault database.
    """
    try:
        notion.pages.create(
            parent={"database_id": HEADLINE_VAULT_DB_ID},
            properties={
                "Headline Vault": {"title": [{"text": {"content": headline}}]},
                "Date Ingested": {"date": {"start": date_ingested}},
                "Relevance Score": {"number": relevance_score},
                "Viral Score": {"number": viral_score},
                "Used?": {"checkbox": used},
                "Source": {"url": source_url},
            },
        )
        logging.info(
            f"✅ Logged headline '{headline}' to Notion DB {HEADLINE_VAULT_DB_ID}"
        )
    except Exception as e:
        logging.error(f"❌ Failed to log headline '{headline}' to Notion: {e}")
