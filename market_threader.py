import logging
import re
from datetime import datetime
from coingecko_client import get_top_tokens_data
from gpt_helpers import client as gpt_client
from post_utils import log_tweet
from tweet_limit_guard import has_reached_daily_limit
from dotenv import load_dotenv
import os
import tweepy

load_dotenv()

client = tweepy.Client(
    bearer_token=os.getenv("BEARER_TOKEN"),
    consumer_key=os.getenv("API_KEY"),
    consumer_secret=os.getenv("API_SECRET"),
    access_token=os.getenv("ACCESS_TOKEN"),
    access_token_secret=os.getenv("ACCESS_TOKEN_SECRET")
)

def generate_market_summary_thread():
    tokens = get_top_tokens_data()
    token_lines = [f"- ${t['symbol']}: ${t['price']:.2f} ({t['change']:+.2f}%)" for t in tokens]
    prompt = (
        "Write a 5-part tweet thread summarizing the market conditions for these tokens:\n" +
        "\n".join(token_lines) +
        "\nEach tweet should be short, crypto-native, and under 280 characters. Prefix with 1/5, 2/5, etc."
    )

    try:
        response = gpt_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a crypto commentator writing short tweet threads."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600,
            temperature=0.85
        )
        return [p.strip() for p in response.choices[0].message.content.strip().split("\n") if p.strip()]
    except Exception as e:
        logging.error(f"❌ Error generating market summary thread: {e}")
        return []

def post_market_summary_thread():
    if has_reached_daily_limit():
        logging.warning("🚫 Daily tweet limit reached — skipping market thread.")
        return

    try:
        thread_parts = generate_market_summary_thread()
        if len(thread_parts) < 2:
            logging.warning("⚠️ Market thread too short — skipping.")
            return

        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        header = f"Daily Dobie Market Update [{today_str}]\n"
        first = client.create_tweet(text=header + "\n" + thread_parts[0])
        log_tweet(first.data['id'], thread_parts[0], "market_thread")
        reply_id = first.data['id']

        for p in thread_parts[1:]:
            reply = client.create_tweet(text=p, in_reply_to_tweet_id=reply_id)
            reply_id = reply.data['id']
            log_tweet(reply_id, p, "market_thread")

        logging.info("✅ Posted market summary thread.")
    except Exception as e:
        logging.error(f"❌ Failed to post market summary thread: {e}")