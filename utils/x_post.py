
"""
X Post Utilities: posting tweets, quote tweets, and threads to X.
Now includes retry-safe, non-blocking logic for thread posting.
"""

import logging
import os
import threading
from datetime import datetime, timezone

import tweepy

from .config import (
    LOG_DIR,
    TWITTER_CONSUMER_KEY,
    TWITTER_CONSUMER_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_SECRET,
    BOT_USER_ID,
)

MAX_TWEET_RETRIES = 3

from .limit_guard import has_reached_daily_limit
from .logger import log_tweet

# Logging
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, "x_post.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Tweepy Client
client = tweepy.Client(
    consumer_key=TWITTER_CONSUMER_KEY,
    consumer_secret=TWITTER_CONSUMER_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_SECRET,
    wait_on_rate_limit=True
)


def post_tweet(text: str, category: str = "original"):
    if has_reached_daily_limit():
        logging.warning("[ALERT] Daily tweet limit reached — skipping standalone tweet.")
        return
    try:
        response = client.create_tweet(text=text)
        tweet_id = response.data["id"]
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        url = f"https://x.com/{BOT_USER_ID}/status/{tweet_id}"
        log_tweet(tweet_id, date_str, category, url, 0, 0, 0, 0)
        logging.info(f"[OK] Posted tweet: {url}")
    except Exception as e:
        logging.error(f"[ALERT] Error posting tweet: {e}")


def post_quote_tweet(text: str, tweet_url: str):
    if has_reached_daily_limit():
        logging.warning("🚫 Daily tweet limit reached — skipping quote tweet.")
        return
    try:
        quote_id = tweet_url.rstrip("/").split("/")[-1]
        response = client.create_tweet(text=text, quote_tweet_id=quote_id)
        tweet_id = response.data["id"]
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        url = f"https://x.com/{BOT_USER_ID}/status/{tweet_id}"
        log_tweet(tweet_id, date_str, "quote", url, 0, 0, 0, 0)
        logging.info(f"✅ Posted quote tweet: {url}")
    except Exception as e:
        logging.error(f"❌ Error posting quote tweet: {e}")


def post_thread(thread_parts: list[str], category: str = "thread", previous_id=None, retry=False):
    if has_reached_daily_limit():
        logging.warning("🚫 Daily tweet limit reached — skipping thread.")
        return

    if not thread_parts:
        logging.warning("⚠️ No thread parts provided; skipping thread.")
        return

    logging.info(
        f"{'🔁 Retrying' if retry else '📢 Posting'} thread of {len(thread_parts)} parts under category '{category}'."
    )

    posted = 0
    try:
        if previous_id:
            in_reply_to = previous_id
            parts_to_post = thread_parts
        else:
            first = thread_parts[0]
            if first is None:
                logging.warning("⚠️ First thread part is None — skipping thread.")
                return
            resp = client.create_tweet(text=first)
            tweet_id = resp.data["id"]
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            url = f"https://x.com/{BOT_USER_ID}/status/{tweet_id}"
            log_tweet(tweet_id, date_str, category, url, 0, 0, 0, 0)
            logging.info(f"✅ Posted thread first tweet: {url}")
            in_reply_to = tweet_id
            posted += 1
            parts_to_post = thread_parts[1:]

        for i, part in enumerate(parts_to_post):
            if part is None:
                logging.warning(f"⚠️ Skipping None part {posted+1} in thread_parts")
                continue
            threading.Event().wait(5)
            try:
                resp = client.create_tweet(text=part, in_reply_to_tweet_id=in_reply_to)
                in_reply_to = resp.data["id"]
                reply_url = f"https://x.com/{BOT_USER_ID}/status/{in_reply_to}"
                log_tweet(in_reply_to, datetime.now(timezone.utc).strftime("%Y-%m-%d"), category, reply_url, 0, 0, 0, 0)
                logging.info(f"↪️ Posted thread reply: {reply_url}")
                posted += 1
            except tweepy.TooManyRequests as e:
                logging.warning(f"⚠️ Rate limit hit on part {posted+1}/{len(thread_parts)} — retrying remaining in 15 minutes.")
                schedule_retry_thread(thread_parts[posted:], in_reply_to, category)
                return
            except Exception as e:
                logging.error(f"❌ Error posting thread part {posted+1}: {e}")

    except Exception as e:
        # Final catch-all — no reference to 'part' here to avoid undefined variable errors
        logging.error(f"❌ General error posting thread: {e}")
        return

def schedule_retry_thread(remaining_parts, reply_to_id, category):
    def retry():
        post_thread(remaining_parts, category=category, previous_id=reply_to_id, retry=True)

    logging.info(f"⏳ Scheduling retry for {len(remaining_parts)} parts in 15 minutes.")
    threading.Timer(900, retry).start()

def schedule_retry_single_tweet(part, reply_to_id, category, retries):
    if retries > MAX_TWEET_RETRIES:
        logging.error(f"❌ Max retries reached for tweet — giving up.")
        return

    def retry():
        try:
            resp = client.create_tweet(text=part, in_reply_to_tweet_id=reply_to_id)
            in_reply_to = resp.data["id"]
            reply_url = f"https://x.com/{BOT_USER_ID}/status/{in_reply_to}"
            log_tweet(in_reply_to, datetime.now(timezone.utc).strftime("%Y-%m-%d"), category, reply_url, 0, 0, 0, 0)
            logging.info(f"✅ Retry success: Posted thread reply: {reply_url}")
        except Exception as e:
            error_str = str(e).lower()
            if "timeout" in error_str or "connection" in error_str:
                logging.warning(f"⚠️ Retry {retries} failed — scheduling next retry in 10 minutes.")
                schedule_retry_single_tweet(part, reply_to_id, category, retries=retries+1)
            else:
                logging.error(f"❌ Retry failed with non-retryable error: {e}")

    logging.info(f"⏳ Scheduling retry {retries}/max {MAX_TWEET_RETRIES} for single tweet in 10 minutes.")
    threading.Timer(600, retry).start()
