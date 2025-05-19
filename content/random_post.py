import random
import logging
import csv
import os
from datetime import datetime
from utils.gpt import generate_gpt_tweet
from utils.x_post import post_tweet, post_quote_tweet
from content.reply_handler import reply_to_comments
from utils.text_utils import insert_cashtags, insert_mentions

# XRP prioritization helper
def get_top_xrp_headline(threshold=7):
    try:
        with open("data/scored_headlines.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in sorted(reader, key=lambda r: float(r["score"]), reverse=True):
                if "XRP" in row["headline"].upper() and float(row["score"]) >= threshold:
                    ts = datetime.fromisoformat(row["timestamp"]).date()
                    if ts == datetime.utcnow().date():
                        return row
    except Exception as e:
        print(f"⚠️ Error reading XRP headline: {e}")
    return None

def post_random_content():
    choice = random.choices(
        ["original", "quote", "reply"],
        weights=[0.98, 0.01, 0.01],
        k=1
    )[0]
    logging.info(f"🌀 post_random_content selected: {choice}")

    if choice == "original":
        xrp_used_flag = "logs/xrp_used.flag"
        xrp = None

        if not os.path.exists(xrp_used_flag):
            xrp = get_top_xrp_headline()
            if xrp:
                with open(xrp_used_flag, "w", encoding="utf-8") as f:
                    f.write(xrp["headline"])
                logging.info(f"✅ Using XRP headline: {xrp['headline']}")

        if xrp:
            prompt = f"""Write a witty, well-informed crypto tweet about this XRP-related news headline:
"{xrp['headline']}"
URL: {xrp['url']}
Use the voice of Hunter: clever, non-hype, ends with '- Hunter 🐾'.
Include 1-2 relevant hashtags and a cashtag for $XRP."""
        else:
            prompt = "Write a standalone crypto tweet. It should be engaging, Web3-native, and end with '- Hunter 🐾'."

        text = generate_gpt_tweet(prompt)
        if text:
            text = insert_cashtags(text)
            text = insert_mentions(text)
            post_tweet(text)

    elif choice == "quote":
        tweet_url = get_recent_viral_tweet()
        if tweet_url:
            prompt = f"Write a witty, insightful quote tweet to this post: {tweet_url}"
            text = generate_gpt_tweet(prompt)
            if text:
                post_quote_tweet(text, tweet_url)

    elif choice == "reply":
        bot_id = os.getenv("BOT_USER_ID")
        if bot_id:
            reply_to_comments(bot_id)

def get_recent_viral_tweet():
    return "https://x.com/coinbureau/status/1790104194723973536"