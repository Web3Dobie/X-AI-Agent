"""
Random Post Module: chooses between original standalone tweet,
quote retweet, or reply to engage audiences with dynamic content.
"""

import csv
import logging
import os
import random
from datetime import datetime

from content.reply_handler import reply_to_comments
from utils import (DATA_DIR, LOG_DIR, generate_gpt_tweet, insert_cashtags,
                   insert_mentions, post_quote_tweet, post_tweet)

# Configure logging
log_file = os.path.join(LOG_DIR, "random_post.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Path to scored headlines CSV
HEADLINE_LOG = os.path.join(DATA_DIR, "scored_headlines.csv")
# Flag file to prevent multiple XRP tweets per day
XRP_FLAG = os.path.join(LOG_DIR, "xrp_used.flag")


def get_top_xrp_headline(threshold=7):
    """
    Return today's top XRP headline with score >= threshold.
    """
    if not os.path.exists(HEADLINE_LOG):
        logging.warning("Scored headlines file not found.")
        return None
    try:
        with open(HEADLINE_LOG, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = sorted(reader, key=lambda r: float(r.get("score", 0)), reverse=True)
            today_str = datetime.utcnow().date().isoformat()
            for row in rows:
                if (
                    "XRP" in row.get("headline", "").upper()
                    and float(row.get("score", 0)) >= threshold
                ):
                    ts = datetime.fromisoformat(row.get("timestamp")).date().isoformat()
                    if ts == today_str:
                        return row
    except Exception as e:
        logging.error(f"Error fetching XRP headline: {e}")
    return None


def post_random_content():
    """
    With 98% probability post original tweet,
    1% quote retweet, 1% reply to mentions.
    """
    choice = random.choices(
        ["original", "quote", "reply"], weights=[0.98, 0.01, 0.01], k=1
    )[0]
    logging.info(f"Selected random post type: {choice}")

    if choice == "original":
        xrp = None
        if not os.path.exists(XRP_FLAG):
            xrp = get_top_xrp_headline()
            if xrp:
                # mark that we've used XRP today
                os.makedirs(LOG_DIR, exist_ok=True)
                with open(XRP_FLAG, "w", encoding="utf-8") as f:
                    f.write(xrp["headline"])
                logging.info(f"Using XRP headline: {xrp['headline']}")

        if xrp:
            prompt = (
                f"Write a witty, insightful tweet about this XRP-related news headline: "
                f"'{xrp['headline']}' URL: {xrp['url']} "
                "Use the voice of Hunter: clever, non-hype, ends with '— Hunter 🐾'. "
                "Include 1-2 relevant hashtags."
            )
        else:
            prompt = (
                "Write a standalone crypto tweet. It should be engaging, Web3-native, "
                "and end with '— Hunter 🐾'."
            )

        text = generate_gpt_tweet(prompt)
        if text:
            text = insert_cashtags(text)
            text = insert_mentions(text)
            post_tweet(text)

    elif choice == "quote":
        # Placeholder function to get a tweet URL to quote
        tweet_url = get_recent_viral_tweet()
        if tweet_url:
            prompt = f"Write a witty quote tweet for this post: {tweet_url}"
            text = generate_gpt_tweet(prompt)
            if text:
                post_quote_tweet(text, tweet_url)

    else:  # reply
        bot_id = os.getenv("BOT_USER_ID")
        if bot_id:
            reply_to_comments(bot_id)


def get_recent_viral_tweet():
    """
    Placeholder: return a recent viral tweet URL for quote retweets.
    """
    # Example static URL; replace with dynamic logic if available
    return "https://x.com/coinbureau/status/1790104194723973536"
