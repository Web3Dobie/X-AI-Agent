import csv
from datetime import datetime

MAX_TWEETS_PER_DAY = 15

def has_reached_daily_limit():
    try:
        with open("logs/tweet_log.csv", newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            today = datetime.utcnow().date().isoformat()
            today_count = sum(1 for row in reader if row["timestamp"].startswith(today))
            return today_count >= MAX_TWEETS_PER_DAY
    except FileNotFoundError:
        return False  # No tweets logged yet