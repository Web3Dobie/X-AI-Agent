import os
import logging
import time
import tweepy
from dotenv import load_dotenv
from utils.limit_guard import has_reached_daily_limit
from utils.logger import log_tweet
from datetime import datetime

load_dotenv()

client = tweepy.Client(
    consumer_key=os.getenv("API_KEY"),
    consumer_secret=os.getenv("API_SECRET"),
    access_token=os.getenv("ACCESS_TOKEN"),
    access_token_secret=os.getenv("ACCESS_TOKEN_SECRET")
)

def post_tweet(text, category="original"):
    if has_reached_daily_limit():
        logging.warning("🚫 Daily tweet limit reached — skipping.")
        return
    try:
        response = client.create_tweet(text=text)
        tweet_id = response.data["id"]
        date = datetime.utcnow().strftime("%Y-%m-%d")
        url = f"https://x.com/{os.getenv('X_USERNAME')}/status/{tweet_id}"
        log_tweet(tweet_id, date, category, url, 0, 0, 0, 0)
        # metrics = client.get_tweet(id=tweet_id, tweet_fields=["public_metrics"])
        # m = metrics.data["public_metrics"]
        # log_tweet(tweet_id, date, category, url, m["like_count"], m["retweet_count"], m["reply_count"], 0)
        logging.info(f"✅ Posted tweet: {url}")
    except Exception as e:
        logging.error(f"❌ Error posting tweet: {e}")

def post_quote_tweet(text, tweet_url):
    if has_reached_daily_limit():
        logging.warning("🚫 Daily tweet limit reached — skipping.")
        return
    try:
        response = client.create_tweet(text=text, quote_tweet_id=tweet_url.split("/")[-1])
        tweet_id = response.data["id"]
        date = datetime.utcnow().strftime("%Y-%m-%d")
        url = f"https://x.com/{os.getenv('X_USERNAME')}/status/{tweet_id}"
        # metrics = client.get_tweet(id=tweet_id, tweet_fields=["public_metrics"])
        # m = metrics.data["public_metrics"]
        # log_tweet(tweet_id, date, "quote", url, m["like_count"], m["retweet_count"], m["reply_count"], 0)
        # logging.info(f"✅ Posted quote tweet: {url}")
        log_tweet(tweet_id, date, "quote", url, 0, 0, 0, 0)
        logging.info(f"✅ Posted quote tweet: {url}")
    except Exception as e:
        logging.error(f"❌ Error posting quote tweet: {e}")

def post_thread(thread_parts, category="thread"):
    if has_reached_daily_limit():
        logging.warning("🚫 Daily tweet limit reached — skipping.")
        return

    logging.info(f"📢 Posting thread: {category}")

    try:
        response = client.create_tweet(text=thread_parts[0])
        tweet_id = response.data["id"]
        date = datetime.utcnow().strftime("%Y-%m-%d")
        url = f"https://x.com/{os.getenv('X_USERNAME')}/status/{tweet_id}"
        log_tweet(tweet_id, date, category, url, 0, 0, 0, 0)
        # try:
        #    metrics = client.get_tweet(id=tweet_id, tweet_fields=["public_metrics"])
        #    m = metrics.data["public_metrics"]
        #    log_tweet(tweet_id, date, category, url, m["like_count"], m["retweet_count"], m["reply_count"], 0)
        # except Exception as e:
        #    logging.warning(f"⚠️ Could not fetch metrics or log tweet: {e}")
        #    log_tweet(tweet_id, date, category, url, 0, 0, 0, 0)

        in_reply_to = tweet_id
        for part in thread_parts[1:]:
            time.sleep(1.5)
            response = client.create_tweet(text=part, in_reply_to_tweet_id=in_reply_to)
            in_reply_to = response.data["id"]

        logging.info(f"✅ Posted thread with {len(thread_parts)} tweets.")
    except Exception as e:
        logging.error(f"❌ Failed to post thread: {e}")