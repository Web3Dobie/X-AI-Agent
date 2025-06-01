"""
Reply Handler Module: scans mentions of the bot on X and replies once per run.
Centralizes logging to LOG_DIR and uses utils/gpt for reply generation.
"""

import logging
import os
import time
from datetime import datetime

import tweepy
from dotenv import load_dotenv

from utils import LOG_DIR, generate_gpt_tweet, log_tweet

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
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_KEY_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET"),
    wait_on_rate_limit=True,
)


def reply_to_comments(bot_id=None):
    """
    Scans the most recent mentions of the bot and replies to the first valid one.
    """
    if not bot_id:
        logging.error("⚠️ Missing bot user ID")
        return

    logging.info("💬 Scanning for recent mentions to respond to")

    try:
        mentions = client.get_users_mentions(id=bot_id, max_results=10)
        data = mentions.data or []
        if not data:
            logging.info("👀 No new mentions found.")
            return

        for tweet in data:
            if tweet.in_reply_to_user_id != int(bot_id):
                continue  # Only respond to mentions of our tweets

            tweet_id = tweet.id
            prompt_text = tweet.text.strip()
            logging.info(f"✍️ Generating reply for tweet ID {tweet_id}")

            # Generate GPT-based reply
            reply = generate_gpt_tweet(prompt_text)
            if not reply:
                logging.warning("⚠️ GPT returned empty reply; skipping")
                continue

            # Post reply
            response = client.create_tweet(text=reply, in_reply_to_tweet_id=tweet_id)
            new_tweet_id = response.data["id"]
            username = os.getenv("X_USERNAME")
            reply_url = f"https://x.com/{username}/status/{new_tweet_id}"

            # Log the reply tweet
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            log_tweet(new_tweet_id, date_str, "reply", reply_url, 0, 0, 0, 0)
            logging.info(f"✅ Replied to mention: {reply_url}")

            # Sleep to respect rate limits
            time.sleep(3)
            break  # Only reply to one mention per execution

    except Exception as e:
        logging.error(f"❌ Error in reply_to_comments: {e}")
