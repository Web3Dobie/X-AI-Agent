import csv
import os
from datetime import datetime

LOG_FILE = "data/tweet_log.csv"
MAX_DAILY_TWEETS = 17  # You can change this based on your tier

def has_reached_daily_limit():
    if not os.path.exists(LOG_FILE):
        return False

    today = datetime.utcnow().strftime("%Y-%m-%d")
    count = 0
    with open(LOG_FILE, newline='', encoding='utf-8') as csvfile:
        for row in csv.DictReader(csvfile):
            if row['date'] == today:
                count += 1
    return count >= MAX_DAILY_TWEETS