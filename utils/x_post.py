"""
X Post Utilities: posting tweets, quote tweets, and threads to X.
Includes retry-safe, non-blocking logic and HTTP timing for diagnostics.
"""

import logging
import http.client as http_client
import os
import threading
import time
from datetime import datetime, timezone
import tweepy

from utils.telegram_log_handler import TelegramHandler
from .config import (
    LOG_DIR,
    TWITTER_CONSUMER_KEY,
    TWITTER_CONSUMER_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_SECRET,
    BOT_USER_ID,
)
from .limit_guard import has_reached_daily_limit
from .logger import log_tweet

# ─── HTTP & Library Debug Setup ─────────────────────────────────────────
# Enable HTTPConnection debug for low-level connection tracing
http_client.HTTPConnection.debuglevel = 1
logging.getLogger('urllib3').setLevel(logging.DEBUG)
logging.getLogger('tweepy').setLevel(logging.DEBUG)

# ─── Logging: File + Telegram ────────────────────────────────────────────
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, 'x_post.log')
logging.basicConfig(
    filename=log_file,
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
# Telegram handler for errors
tg_handler = TelegramHandler()
tg_handler.setLevel(logging.ERROR)
tg_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)
logging.getLogger().addHandler(tg_handler)

# ─── Tweepy Client Initialization ────────────────────────────────────────
client = tweepy.Client(
    consumer_key=TWITTER_CONSUMER_KEY,
    consumer_secret=TWITTER_CONSUMER_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_SECRET,
    wait_on_rate_limit=True,
)

MAX_TWEET_RETRIES = 3

# ─── Timing Wrapper ─────────────────────────────────────────────────────
def timed_create_tweet(text: str, in_reply_to_tweet_id=None, part_index: int = None):
    """
    Wraps client.create_tweet to log duration and re-raise exceptions.
    """
    start = time.monotonic()
    try:
        resp = client.create_tweet(
            text=text,
            in_reply_to_tweet_id=in_reply_to_tweet_id
        )
    except Exception:
        elapsed = time.monotonic() - start
        logging.debug(f"HTTP POST /2/tweets failed after {elapsed:.2f}s (part {part_index})")
        raise
    else:
        elapsed = time.monotonic() - start
        logging.debug(f"HTTP POST /2/tweets succeeded in {elapsed:.2f}s (part {part_index})")
        return resp

# ─── Standalone Tweet ────────────────────────────────────────────────────
def post_tweet(text: str, category: str = 'original'):
    if has_reached_daily_limit():
        logging.warning('🚫 Daily tweet limit reached — skipping standalone tweet.')
        return
    try:
        resp = timed_create_tweet(text=text, part_index=1)
        tweet_id = resp.data['id']
        date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        url = f"https://x.com/{BOT_USER_ID}/status/{tweet_id}"
        log_tweet(tweet_id, date_str, category, url, 0, 0, 0, 0)
        logging.info(f"✅ Posted tweet: {url}")
    except Exception as e:
        logging.error(f"❌ Error posting tweet: {e}")

# ─── Quote Tweet ────────────────────────────────────────────────────────
def post_quote_tweet(text: str, tweet_url: str):
    if has_reached_daily_limit():
        logging.warning('🚫 Daily tweet limit reached — skipping quote tweet.')
        return
    try:
        quote_id = tweet_url.rstrip('/').split('/')[-1]
        resp = client.create_tweet(text=text, quote_tweet_id=quote_id)
        tweet_id = resp.data['id']
        date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        url = f"https://x.com/{BOT_USER_ID}/status/{tweet_id}"
        log_tweet(tweet_id, date_str, 'quote', url, 0, 0, 0, 0)
        logging.info(f"✅ Posted quote tweet: {url}")
    except Exception as e:
        logging.error(f"❌ Error posting quote tweet: {e}")

# ─── Thread Posting ─────────────────────────────────────────────────────
def post_thread(thread_parts: list[str], category: str = 'thread', previous_id=None, retry=False):
    if has_reached_daily_limit():
        logging.warning('🚫 Daily tweet limit reached — skipping thread.')
        return {
            "posted": 0,
            "total": len(thread_parts) if thread_parts else 0,
            "error": "Daily limit reached"
        }

    if not thread_parts:
        logging.warning('⚠️ No thread parts provided; skipping thread.')
        return {
            "posted": 0,
            "total": 0,
            "error": "No thread parts provided"
        }

    logging.info(f"{'🔁 Retrying' if retry else '📢 Posting'} thread of {len(thread_parts)} parts under category '{category}'.")
    posted = 0
    try:
        # First tweet
        if previous_id:
            in_reply_to = previous_id
            parts_to_post = thread_parts
        else:
            first = thread_parts[0]
            resp = timed_create_tweet(text=first, part_index=1)
            tweet_id = resp.data['id']
            date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            url = f"https://x.com/{BOT_USER_ID}/status/{tweet_id}"
            log_tweet(tweet_id, date_str, category, url, 0, 0, 0, 0)
            logging.info(f"✅ Posted thread first tweet: {url}")
            in_reply_to = tweet_id
            posted = 1
            parts_to_post = thread_parts[1:]

        # Replies
        for part in parts_to_post:
            if not part:
                logging.warning(f"⚠️ Skipping empty part {posted+1}")
                continue
            time.sleep(5)
            try:
                resp = timed_create_tweet(text=part, in_reply_to_tweet_id=in_reply_to, part_index=posted+1)
                in_reply_to = resp.data['id']
                reply_url = f"https://x.com/{BOT_USER_ID}/status/{in_reply_to}"
                log_tweet(in_reply_to, datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'), category, reply_url, 0, 0, 0, 0)
                logging.info(f"↪️ Posted thread reply: {reply_url}")
                posted += 1
            except tweepy.TooManyRequests:
                logging.warning(f"⚠️ Rate limit hit on part {posted+1} — scheduling retry.")
                schedule_retry_thread(thread_parts[posted:], in_reply_to, category)
                return
            except Exception as e:
                logging.error(f"❌ Error posting part {posted+1}: {e}")
                raise

        return {
            "posted": posted,
            "total": len(thread_parts)
        }

    except Exception as e:
        logging.error(f"❌ General error posting thread: {e}")
        return {
            "posted": posted,
            "total": len(thread_parts),
            "error": str(e)
        }


# ─── Retry Schedulers ───────────────────────────────────────────────────
def schedule_retry_thread(remaining_parts: list[str], reply_to_id: str, category: str):
    logging.info(f"⏳ Scheduling retry for {len(remaining_parts)} parts in 15 minutes.")
    def retry_call():
        post_thread(remaining_parts, category=category, previous_id=reply_to_id, retry=True)
    threading.Timer(900, retry_call).start()


def schedule_retry_single_tweet(part: str, reply_to_id: str, category: str, retries: int = 1):
    if retries > MAX_TWEET_RETRIES:
        logging.error('❌ Max retries reached for single tweet — giving up.')
        return

    logging.info(f"⏳ Scheduling retry {retries}/{MAX_TWEET_RETRIES} for single tweet in 10 minutes.")
    def retry_call():
        try:
            resp = timed_create_tweet(text=part, in_reply_to_tweet_id=reply_to_id, part_index=None)
            in_reply = resp.data['id']
            reply_url = f"https://x.com/{BOT_USER_ID}/status/{in_reply}"
            log_tweet(in_reply, datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'), category, reply_url, 0, 0, 0, 0)
            logging.info(f"✅ Retry success: Posted single tweet: {reply_url}")
        except Exception as e:
            error_str = str(e).lower()
            if 'timeout' in error_str or 'connection' in error_str:
                schedule_retry_single_tweet(part, reply_to_id, category, retries=retries+1)
            else:
                logging.error(f"❌ Retry failed with non-retryable error: {e}")
    threading.Timer(600, retry_call).start()
