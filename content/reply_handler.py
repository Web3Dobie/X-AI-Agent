import logging
import os
import time
import csv
from datetime import datetime

import tweepy
from dotenv import load_dotenv

from utils import LOG_DIR, generate_gpt_tweet
from utils.config import TWITTER_BEARER_TOKEN

load_dotenv()

# Configure logging
log_file = os.path.join(LOG_DIR, "reply_handler.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Initialize tweepy client
client = tweepy.Client(
    bearer_token=TWITTER_BEARER_TOKEN,
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_KEY_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET"),
    wait_on_rate_limit=False,
)

MAX_REPLIES_PER_RUN = 1

def load_own_tweet_ids():
    """
    Load tweet IDs from tweet_log.csv
    """
    tweet_ids = set()
    try:
        with open('data/tweet_log.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                tweet_ids.add(row['tweet_id'])
        logging.info(f"📄 Loaded {len(tweet_ids)} own tweet IDs for reply matching.")
    except Exception as e:
        logging.error(f"❌ Failed to load tweet_log.csv: {e}")
    return tweet_ids

def reply_to_comments(bot_id=None):
    """
    Scans mentions and replies to tweets that are direct replies to our own tweets.
    """
    if not bot_id:
        logging.error("⚠️ Missing bot user ID")
        return

    own_tweet_ids = load_own_tweet_ids()
    if not own_tweet_ids:
        logging.warning("⚠️ No tweet IDs loaded — skipping replies.")
        return

    logging.info(f"💬 Scanning for recent mentions with bot_id={bot_id}")
    replies_sent = 0

    try:
        logging.info("⏱ Calling get_users_mentions")
        start = time.time()
        mentions = client.get_users_mentions(id=bot_id, max_results=5)
        elapsed = time.time() - start
        logging.info(f"✅ get_users_mentions completed in {elapsed:.2f} seconds")

    except tweepy.TooManyRequests as e:
        reset_ts = int(e.response.headers.get("x-rate-limit-reset", 0))
        reset_time = datetime.fromtimestamp(reset_ts)
        wait_seconds = reset_ts - int(time.time())
        logging.warning(f"🚦 Rate limit hit. Can retry after {reset_time} UTC (in {wait_seconds} seconds)")
        return

    except tweepy.TweepyException as e:
        logging.error(f"❌ Tweepy error fetching mentions: {e}")
        return

    except Exception as e:
        logging.error(f"❌ General error fetching mentions: {e}")
        return

    data = mentions.data or []
    if not data:
        logging.info("👀 No new mentions found.")
        return

    for tweet in data:
        try:
            full_tweet = client.get_tweet(tweet.id, tweet_fields=["in_reply_to_status_id"])
            in_reply_to_status_id = getattr(full_tweet.data, "in_reply_to_status_id", None)
        except tweepy.TweepyException as e:
            logging.error(f"❌ Tweepy error fetching tweet {tweet.id}: {e}")
            continue
        except Exception as e:
            logging.error(f"❌ General error fetching tweet {tweet.id}: {e}")
            continue

        logging.debug(f"Processing {tweet.id}: in_reply_to_status_id={in_reply_to_status_id}")

        if not in_reply_to_status_id:
            logging.debug(f"Skipping {tweet.id}: not a reply to any tweet")
            continue

        if str(in_reply_to_status_id) not in own_tweet_ids:
            logging.debug(f"Skipping {tweet.id}: not a reply to our tweet")
            continue

        # Valid reply — proceed
        tweet_id = tweet.id
        prompt_text = tweet.text.strip()
        logging.info(f"✍️ Generating reply for tweet ID {tweet_id} with text: {prompt_text}")

        reply = generate_gpt_tweet(prompt_text)
        if not reply:
            logging.warning("⚠️ GPT returned empty reply; skipping")
            continue

        try:
            response = client.create_tweet(text=reply, in_reply_to_tweet_id=tweet_id)
            new_tweet_id = response.data["id"]
            username = os.getenv("X_USERNAME")
            reply_url = f"https://x.com/{username}/status/{new_tweet_id}"

            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            # Assuming you have log_tweet imported
            log_tweet(new_tweet_id, date_str, "reply", reply_url, 0, 0, 0, 0)
            logging.info(f"✅ Replied to mention: {reply_url}")

            replies_sent += 1
            if replies_sent >= MAX_REPLIES_PER_RUN:
                logging.info(f"🔒 Reached max replies per run: {MAX_REPLIES_PER_RUN}")
                break

            time.sleep(3)

        except tweepy.TooManyRequests as e:
            reset_ts = int(e.response.headers.get("x-rate-limit-reset", 0))
            reset_time = datetime.fromtimestamp(reset_ts)
            wait_seconds = reset_ts - int(time.time())
            logging.warning(f"🚦 Rate limit hit while posting reply. Can retry after {reset_time} UTC (in {wait_seconds} seconds)")
            return

        except tweepy.TweepyException as e:
            logging.error(f"❌ Tweepy error posting reply: {e}")
            continue

        except Exception as e:
            logging.error(f"❌ General error posting reply: {e}")
            continue

    if replies_sent == 0:
        logging.info("✅ Finished processing mentions — no replies sent this run.")
