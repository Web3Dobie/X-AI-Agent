"""
X Post Utilities: A dedicated service for posting tweets, quote tweets, and threads.
This module is now decoupled from any specific logging system. The calling functions
are responsible for logging the results.
"""

import logging
import time
from datetime import datetime, timezone
import tweepy
import requests

# Centralized configuration import from the main settings file
from .config import (
    TWITTER_CONSUMER_KEY,
    TWITTER_CONSUMER_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_TOKEN_SECRET,
    BOT_USER_ID,
)
from .rate_limit_manager import is_rate_limited, update_rate_limit_state_from_headers, decrement_rate_limit_counter

# This module now inherits its logging configuration from scheduler.py
logger = logging.getLogger(__name__)

# ─── Tweepy Client Initialization ────────────────────────────────────────
client = tweepy.Client(
    consumer_key=TWITTER_CONSUMER_KEY,
    consumer_secret=TWITTER_CONSUMER_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
    wait_on_rate_limit=True,
)
auth = tweepy.OAuth1UserHandler(
    TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET,
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
)
api = tweepy.API(auth)


# ─── Helper Functions ───────────────────────────────────────────────────

def timed_create_tweet(retry_count=0, **kwargs):
    """Wrapped tweet creation with timing, retries and error handling."""
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAYS = [300, 600, 900]
    start_time = time.monotonic()
    try:
        resp = client.create_tweet(**kwargs)
        elapsed = time.monotonic() - start_time
        logger.debug(f"HTTP POST /2/tweets succeeded in {elapsed:.2f}s")
        return resp
    except (tweepy.errors.TweepyException, requests.exceptions.RequestException, ConnectionError) as e:
        error_str = str(e).lower()
        if ('timeout' in error_str or 'connection' in error_str) and retry_count < MAX_RETRY_ATTEMPTS:
            delay = RETRY_DELAYS[retry_count]
            logger.warning(f"Connection issue on attempt {retry_count + 1}/{MAX_RETRY_ATTEMPTS}. Retrying in {delay}s")
            time.sleep(delay)
            return timed_create_tweet(retry_count + 1, **kwargs)
        logger.error(f"HTTP POST /2/tweets failed: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred in timed_create_tweet: {e}", exc_info=True)
        raise

def upload_media(image_path):
    """Uploads an image to Twitter/X and returns the media_id."""
    try:
        media = api.media_upload(filename=image_path)
        return media.media_id
    except Exception as e:
        logger.error(f"❌ Failed to upload media {image_path}: {e}")
        return None

# ─── Posting Functions (All refactored to return a dictionary) ───────────

def post_tweet(text: str, category: str = 'original'):
    if is_rate_limited(): # This check is still correct
        logging.warning('🚫 Daily tweet limit reached — skipping standalone tweet.')
        return {"final_tweet_id": None, "error": "Daily limit reached"}
    try:
        resp = timed_create_tweet(text=text)
        
        # <<< CHANGED: Use the new decrement function on success
        decrement_rate_limit_counter()
        
        tweet_id = resp.data['id']
        logger.info(f"✅ Posted tweet: https://x.com/{BOT_USER_ID}/status/{tweet_id}")
        return {"final_tweet_id": tweet_id, "error": None}
        
    except tweepy.errors.TooManyRequests as e:
        # This part is correct, it uses the headers from the error response
        logging.warning("Rate limit hit while posting tweet.")
        if e.response: update_rate_limit_state_from_headers(e.response.headers)
        return {"final_tweet_id": None, "error": "Rate limit hit"}

    except Exception as e:
        logger.error(f"❌ Error posting tweet: {e}", exc_info=True)
        return {"final_tweet_id": None, "error": str(e)}

def post_tweet_with_media(text: str, image_path: str, category: str = 'original'):
    """Posts a tweet with a single image."""
    if is_rate_limited():
        logging.warning('🚫 Daily tweet limit reached — skipping tweet with media.')
        return {"final_tweet_id": None, "error": "Daily limit reached"}
    try:
        media_id = upload_media(image_path)
        if not media_id:
            raise Exception("Media upload failed.")
            
        resp = timed_create_tweet(text=text, media_ids=[media_id])
        update_rate_limit_state_from_headers(resp.headers)
        
        tweet_id = resp.data['id']
        url = f"https://x.com/{BOT_USER_ID}/status/{tweet_id}"
        logger.info(f"✅ Posted tweet with image: {url}")
        
        return {"final_tweet_id": tweet_id, "error": None}

    except tweepy.errors.TooManyRequests as e:
        logging.warning("Rate limit hit while posting tweet with media.")
        if e.response: update_rate_limit_state_from_headers(e.response.headers)
        return {"final_tweet_id": None, "error": "Rate limit hit"}
    except Exception as e:
        logger.error(f"❌ Error posting tweet with media: {e}", exc_info=True)
        return {"final_tweet_id": None, "error": str(e)}

def post_quote_tweet(text: str, tweet_url: str, category: str = 'quote'):
    """Posts a quote tweet."""
    if is_rate_limited():
        logging.warning('🚫 Daily tweet limit reached — skipping quote tweet.')
        return {"final_tweet_id": None, "error": "Daily limit reached"}
    try:
        quote_id = tweet_url.rstrip('/').split('/')[-1]
        resp = client.create_tweet(text=text, quote_tweet_id=quote_id)
        update_rate_limit_state_from_headers(resp.headers)
        
        tweet_id = resp.data['id']
        url = f"https://x.com/{BOT_USER_ID}/status/{tweet_id}"
        logger.info(f"✅ Posted quote tweet: {url}")
        
        return {"final_tweet_id": tweet_id, "error": None}
        
    except tweepy.errors.TooManyRequests as e:
        logging.warning("Rate limit hit while posting quote tweet.")
        if e.response: update_rate_limit_state_from_headers(e.response.headers)
        return {"final_tweet_id": None, "error": "Rate limit hit"}
    except Exception as e:
        logger.error(f"❌ Error posting quote tweet: {e}", exc_info=True)
        return {"final_tweet_id": None, "error": str(e)}

def post_thread(thread_parts: list[str], category: str = 'thread', media_id_first=None, retry=False):
    """Posts a sequence of tweets as a thread."""
    if is_rate_limited():
        logging.warning('🚫 Daily tweet limit reached — skipping thread.')
        return {"posted": 0, "total": len(thread_parts), "final_tweet_id": None, "error": "Daily limit reached"}
    
    if not thread_parts:
        logging.warning('⚠️ No thread parts provided; skipping thread.')
        return {"posted": 0, "total": 0, "final_tweet_id": None, "error": "No thread parts provided"}

    logging.info(f"{'🔁 Retrying' if retry else '📢 Posting'} thread of {len(thread_parts)} parts under category '{category}'.")
    
    posted_count = 0
    in_reply_to = None

    try:
        # First tweet
        first_part = thread_parts[0]
        resp = timed_create_tweet(text=first_part, media_ids=[media_id_first] if media_id_first else None)
        decrement_rate_limit_counter()
        in_reply_to = resp.data['id']
        posted_count = 1
        
        # Replies
        for part in thread_parts[1:]:
            if is_rate_limited():
                logging.warning("🚫 Daily limit reached mid-thread. Stopping.")
                break
            
            time.sleep(5) # Small delay between thread parts
            resp = timed_create_tweet(text=part, in_reply_to_tweet_id=in_reply_to)
            decrement_rate_limit_counter()
            in_reply_to = resp.data['id']
            posted_count += 1

    except tweepy.errors.TooManyRequests as e:
        # This block handles only the rate limit error
        logging.warning(f"Hit rate limit mid-thread after posting {posted_count} parts.")
        if e.response: 
            update_rate_limit_state_from_headers(e.response.headers)
    
    except Exception as e:
        # This block is now separate and handles all other potential errors
        logging.error(f"❌ Thread posting failed after {posted_count} parts: {e}", exc_info=True)
    
    # The 'return' statement comes after all the except blocks
    return {
        "posted": posted_count,
        "total": len(thread_parts),
        "final_tweet_id": in_reply_to,
        "error": None if posted_count == len(thread_parts) else "Thread incomplete due to an error or rate limit."
    }