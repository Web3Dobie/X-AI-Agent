"""
X Post Utilities: posting tweets, quote tweets, and threads to X.
Uses tweepy.Client for API calls, enforces daily limits, logs metrics, and errors.
"""

import logging
import os
import time
from datetime import datetime, timezone

import tweepy
from dotenv import load_dotenv

from .config import DATA_DIR, LOG_DIR
from .limit_guard import has_reached_daily_limit
from .logger import log_tweet

# Load environment variables
load_dotenv()

# Configure logging
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, "x_post.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Initialize tweepy client
client = tweepy.Client(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_KEY_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET"),
    wait_on_rate_limit=True,
)


def post_tweet(text: str, category: str = "original"):
    """
    Post a standalone tweet.
    """
    if has_reached_daily_limit():
        logging.warning("🚫 Daily tweet limit reached — skipping standalone tweet.")
        return
    try:
        response = client.create_tweet(text=text)
        tweet_id = response.data["id"]
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        url = f"https://x.com/{os.getenv('X_USERNAME')}/status/{tweet_id}"
        log_tweet(tweet_id, date_str, category, url, 0, 0, 0, 0)
        logging.info(f"✅ Posted tweet: {url}")
    except Exception as e:
        logging.error(f"❌ Error posting tweet: {e}")


def post_quote_tweet(text: str, tweet_url: str):
    """
    Post a quote tweet in response to an existing tweet URL.
    """
    if has_reached_daily_limit():
        logging.warning("🚫 Daily tweet limit reached — skipping quote tweet.")
        return
    try:
        quote_id = tweet_url.rstrip("/").split("/")[-1]
        response = client.create_tweet(text=text, quote_tweet_id=quote_id)
        tweet_id = response.data["id"]
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        url = f"https://x.com/{os.getenv('X_USERNAME')}/status/{tweet_id}"
        log_tweet(tweet_id, date_str, "quote", url, 0, 0, 0, 0)
        logging.info(f"✅ Posted quote tweet: {url}")
    except Exception as e:
        logging.error(f"❌ Error posting quote tweet: {e}")


def post_thread(thread_parts: list[str], category: str = "thread"):
    """
    Post a multi-part thread on X.
    """
    if has_reached_daily_limit():
        logging.warning("🚫 Daily tweet limit reached — skipping thread.")
        return
    if not thread_parts:
        logging.warning("⚠️ No thread parts provided; skipping thread.")
        return

    logging.info(
        f"📢 Posting thread of {len(thread_parts)} parts under category '{category}'."
    )
    try:
        # Post first tweet
        first = thread_parts[0]
        resp = client.create_tweet(text=first)
        tweet_id = resp.data["id"]
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        url = f"https://x.com/{os.getenv('X_USERNAME')}/status/{tweet_id}"
        log_tweet(tweet_id, date_str, category, url, 0, 0, 0, 0)
        logging.info(f"✅ Posted thread first tweet: {url}")

        in_reply_to = tweet_id
        for part in thread_parts[1:]:
            time.sleep(5)
            try:
                resp = client.create_tweet(text=part, in_reply_to_tweet_id=in_reply_to)
                in_reply_to = resp.data["id"]
                reply_url = (
                    f"https://x.com/{os.getenv('X_USERNAME')}/status/{in_reply_to}"
                )
                log_tweet(in_reply_to, date_str, category, reply_url, 0, 0, 0, 0)
                logging.info(f"↪️ Posted thread reply: {reply_url}")
            except Exception as e:
                logging.error(f"❌ Error posting thread reply: {e}")
    except Exception as e:
        logging.error(f"❌ Failed to post thread: {e}")
