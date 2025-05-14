import logging
from datetime import datetime
from headline_manager import get_top_headline
from gpt_helpers import client as gpt_client
from post_utils import log_tweet
from tweet_limit_guard import has_reached_daily_limit
from dotenv import load_dotenv
import tweepy
import os

load_dotenv()

client = tweepy.Client(
    bearer_token=os.getenv("BEARER_TOKEN"),
    consumer_key=os.getenv("API_KEY"),
    consumer_secret=os.getenv("API_SECRET"),
    access_token=os.getenv("ACCESS_TOKEN"),
    access_token_secret=os.getenv("ACCESS_TOKEN_SECRET")
)

def post_top_news_thread():
    if has_reached_daily_limit():
        logging.warning("🚫 Daily tweet limit reached — skipping top news opinion.")
        return

    try:
        headline, url, ticker = get_top_headline()
        prompt = (
            f"Write a short, opinionated 3-part Twitter thread about this crypto headline:\n"
            f"'{headline}'\n\n"
            f"Include context, reaction, and insight. Be crypto-native but concise. Max 280 characters per tweet. "
            f"Add a final tweet with the source link: {url}"
        )

        response = gpt_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are Hunter, a Web3 opinion machine with a Doberman's bite. React boldly, stay crypto-native, and end every tweet with '— Hunter 🐾'."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600,
            temperature=0.85
        )

        thread_parts = [p.strip() for p in response.choices[0].message.content.strip().split("\n") if p.strip()]
        if not thread_parts or len(thread_parts) < 2:
            logging.warning("⚠️ Top news thread too short — skipping.")
            return

        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        header = f"Daily Dobie Opinion 🧵 [{today_str}]\n"
        first = client.create_tweet(text=header + "\n" + thread_parts[0])
        log_tweet(first.data['id'], thread_parts[0], "news_opinion_thread")
        reply_id = first.data['id']

        for part in thread_parts[1:]:
            try:
                reply = client.create_tweet(text=part, in_reply_to_tweet_id=reply_id)
                reply_id = reply.data['id']
                log_tweet(reply_id, part, "news_opinion_thread")
            except Exception as e:
                logging.error(f"❌ Failed to post thread part: {e}")

        logging.info("🧵 Posted top news opinion thread.")
    except Exception as e:
        logging.error(f"❌ Error generating or posting top news thread: {e}")