import csv
import logging
from datetime import datetime
from notion_logger import log_tweet
import os

TWEET_LOG = "logs/tweet_log.csv"

def update_from_analytics(analytics_csv_path):
    updated_count = 0
    if not os.path.exists(TWEET_LOG):
        print("tweet_log.csv not found.")
        return

    # Load tweet_log.csv into memory
    with open(TWEET_LOG, newline='', encoding='utf-8') as f:
        log_reader = list(csv.DictReader(f))
        log_map = {row["tweet_id"]: row for row in log_reader}

    # Process analytics CSV
    with open(analytics_csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tweet_id = row.get("Tweet id") or row.get("Tweet ID")
            if tweet_id and tweet_id in log_map:
                tweet_data = log_map[tweet_id]
                date = tweet_data["timestamp"]
                tweet_type = tweet_data["category"]
                url = f"https://x.com/Web3_Dobie/status/{tweet_id}"
                likes = int(row.get("Likes", 0))
                retweets = int(row.get("Retweets", 0))
                replies = int(row.get("Replies", 0))
                engagement = likes + 2 * retweets + replies
                log_tweet(date, tweet_type, url, likes, retweets, replies, engagement)
                updated_count += 1

    print(f"✅ Logged {updated_count} tweet(s) to Notion.")
    if updated_count == 0:
        print("⚠️ No matching tweet IDs found in tweet_log.csv.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python parse_x_metrics.py path_to_analytics.csv")
    else:
        update_from_analytics(sys.argv[1])