import os
import csv
import logging
from notion_logger import log_tweet as log_tweet_to_notion
import tweepy
from dotenv import load_dotenv
from datetime import datetime
from difflib import SequenceMatcher
from tweet_limit_guard import has_reached_daily_limit
from gpt_helpers import generate_unique_gpt_tweet

load_dotenv()

client = tweepy.Client(
    bearer_token=os.getenv("BEARER_TOKEN"),
    consumer_key=os.getenv("API_KEY"),
    consumer_secret=os.getenv("API_SECRET"),
    access_token=os.getenv("ACCESS_TOKEN"),
    access_token_secret=os.getenv("ACCESS_TOKEN_SECRET")
)

def log_tweet(tweet_id, content, category="general"):
    log_path = "logs/tweet_log.csv"
    file_exists = os.path.isfile(log_path)
    with open(log_path, mode="a", newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["tweet_id", "content", "category", "timestamp"])
        writer.writerow([tweet_id, content, category, datetime.utcnow().isoformat()])
        log_tweet_to_notion(
            datetime.utcnow().isoformat(),
            category,
            f"https://x.com/Web3_Dobie/status/{tweet_id}",
            0, 0, 0, 0  # likes, retweets, replies, engagement_score
        )

def is_duplicate_tweet(new_text, threshold=0.85):
    try:
        with open("logs/tweet_log.csv", newline='', encoding='utf-8') as f:
            reader = list(csv.DictReader(f))[-20:]
            for row in reader:
                similarity = SequenceMatcher(None, new_text.lower(), row["content"].lower()).ratio()
                if similarity > threshold:
                    return True
    except FileNotFoundError:
        return False
    return False

def post_original_tweet():
    if has_reached_daily_limit():
        logging.warning("🚫 Daily tweet limit reached — skipping original tweet.")
        return
    tweet = generate_unique_gpt_tweet("Write an original, punchy Web3 tweet.")
    try:
        res = client.create_tweet(text=tweet)
        log_tweet(res.data['id'], tweet, "original")
        logging.info(f"✅ Posted original tweet: {tweet}")
    except Exception as e:
        logging.error(f"❌ Error posting original tweet: {e}")

def post_quote_tweet():
    if has_reached_daily_limit():
        logging.warning("🚫 Daily tweet limit reached — skipping quote tweet.")
        return
    tweet = generate_unique_gpt_tweet("Write a clever quote tweet about a trending crypto topic.")
    try:
        res = client.create_tweet(text=tweet)
        log_tweet(res.data['id'], tweet, "quote")
        logging.info(f"✅ Posted quote tweet: {tweet}")
    except Exception as e:
        logging.error(f"❌ Error posting quote tweet: {e}")

def post_thread():
    if has_reached_daily_limit():
        logging.warning("🚫 Daily tweet limit reached — skipping thread.")
        return
    prompt = "Write a 3-part Web3 thread. Each part under 280 characters."
    from gpt_helpers import client as gpt_client

    try:
        response = gpt_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You write clear, engaging Web3 Twitter threads."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=512,
            temperature=0.9
        )
        content = response.choices[0].message.content.strip()
        parts = [p.strip() for p in content.split("\n") if p.strip()]

        if len(parts) < 2:
            logging.warning("Thread too short — skipping.")
            return

        first = client.create_tweet(text=parts[0])
        log_tweet(first.data['id'], parts[0], "thread")
        reply_id = first.data['id']

        for p in parts[1:]:
            reply = client.create_tweet(text=p, in_reply_to_tweet_id=reply_id)
            reply_id = reply.data['id']
            log_tweet(reply_id, p, "thread")

        logging.info(f"✅ Posted GPT thread.")
    except Exception as e:
        logging.error(f"❌ Error posting GPT thread: {e}")

def post_reply_to_kol():
    import random
    from tweepy import Paginator
    from gpt_helpers import client as gpt_client

    kol_ids = [
        "44196397",   # Elon Musk
        "6253282",    # Vitalik
        "2592325536", # CZ_Binance
        "3225282092", # Coinbase
        "1349776993449263104", # NFT God
        "14338144",   # Naval
        "164137731",  # Balaji
        "240110659",  # RaoulGMI
        "1469605528340406272", # Ledger
        "15485441"    # Chris Dixon
    ]

    if has_reached_daily_limit():
        logging.warning("🚫 Daily tweet limit reached — skipping KOL reply.")
        return

    selected_id = random.choice(kol_ids)
    try:
        tweets = list(Paginator(
            client.get_users_tweets,
            id=selected_id,
            exclude=["retweets", "replies"],
            max_results=5
        ).flatten(limit=10))

        if not tweets:
            logging.warning("⚠️ No tweets fetched for selected KOL.")
            return

        target = random.choice(tweets)
        prompt = f"Reply to this crypto tweet with something insightful or witty. Tweet: {target.text}"
        response = gpt_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You reply like a clever Web3 thought leader on X."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.85
        )
        reply_text = response.choices[0].message.content.strip()
        res = client.create_tweet(text=reply_text, in_reply_to_tweet_id=target.id)
        log_tweet(res.data['id'], reply_text, "reply")
        logging.info(f"💬 Replied to KOL tweet {target.id}: {reply_text}")
    except Exception as e:
        logging.error(f"❌ Error in post_reply_to_kol: {e}")

def reply_to_comments(bot_id):
    import time
    from tweepy import Paginator
    from gpt_helpers import client as gpt_client

    if has_reached_daily_limit():
        logging.warning("🚫 Daily tweet limit reached — skipping comment replies.")
        return

    try:
        tweets = list(Paginator(
            client.get_users_tweets,
            id=bot_id,
            exclude=["retweets", "replies"],
            max_results=5,
            tweet_fields=["id"]
        ).flatten(limit=10))

        if not tweets:
            logging.warning("⚠️ No tweets found for comment monitoring.")
            return

        latest_tweet_ids = [t.id for t in tweets]

        replied = 0
        for target_id in latest_tweet_ids:
            replies = list(Paginator(
                client.get_tweet_replies,
                id=target_id,
                max_results=10,
                tweet_fields=["author_id", "in_reply_to_user_id", "conversation_id"]
            ).flatten(limit=10))

            for r in replies:
                if r.author_id == bot_id:
                    continue  # Skip self-replies
                prompt = f"Reply to this tweet directed at us: {r.text}"
                response = gpt_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an intelligent Web3 assistant engaging respectfully."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=180,
                    temperature=0.75
                )
                reply_text = response.choices[0].message.content.strip()
                res = client.create_tweet(text=reply_text, in_reply_to_tweet_id=r.id)
                log_tweet(res.data['id'], reply_text, "comment")
                logging.info(f"💬 Replied to comment on {target_id}")
                replied += 1
                time.sleep(5)
                if replied >= 2:
                    return
    except Exception as e:
        logging.error(f"❌ Error in reply_to_comments: {e}")