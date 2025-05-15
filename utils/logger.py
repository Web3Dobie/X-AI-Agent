import csv
import os
from datetime import datetime
from utils.notion_logger import log_to_notion

TWEET_LOG = "data/tweet_log.csv"

def log_tweet(tweet_id, date, tweet_type, url, likes, retweets, replies, engagement_score):
    os.makedirs("data", exist_ok=True)
    exists = os.path.exists(TWEET_LOG)
    with open(TWEET_LOG, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not exists:
            writer.writerow(["tweet_id", "date", "type", "url", "likes", "retweets", "replies", "engagement_score"])
        writer.writerow([tweet_id, date, tweet_type, url, likes, retweets, replies, engagement_score])

    try:
        log_to_notion(tweet_id, date, tweet_type, url, likes, retweets, replies, engagement_score)
    except Exception as e:
        print(f"⚠️ Notion log failed: {e}")