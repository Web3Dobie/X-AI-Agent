import logging
import random
import time
import os
from dotenv import load_dotenv
import tweepy
from utils.gpt import generate_gpt_tweet
from utils.logger import log_tweet
from datetime import datetime

load_dotenv()

client = tweepy.Client(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_KEY_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET"),
    wait_on_rate_limit=True
)

def reply_to_comments(bot_id=None):
    if not bot_id:
        logging.error("⚠️ Missing bot user ID")
        return

    logging.info("💬 Scanning for recent replies to respond to...")

    try:
        mentions = client.get_users_mentions(id=bot_id, max_results=10)
        if not mentions.data:
            logging.info("👀 No new mentions found.")
            return

        for tweet in mentions.data:
            if tweet.in_reply_to_user_id != int(bot_id):
                continue  # Only respond to replies to our tweets

            tweet_id = tweet.id
            username = tweet.author_id
            prompt = tweet.text.strip()

            # Generate GPT-based reply
            reply = generate_reply_text(prompt)

            # Post reply
            response = client.create_tweet(text=reply, in_reply_to_tweet_id=tweet_id)
            new_tweet_id = response.data["id"]
            url = f"https://x.com/{os.getenv('X_USERNAME')}/status/{new_tweet_id}"

            date = datetime.utcnow().strftime("%Y-%m-%d")
            log_tweet(new_tweet_id, date, "reply", url, 0, 0, 0, 0)

            logging.info(f"✅ Replied to comment: {url}")
            time.sleep(3)
            break  # reply to only 1 comment per run (safe for Free Tier)

    except Exception as e:
        logging.error(f"❌ Error in reply_to_comments: {e}")