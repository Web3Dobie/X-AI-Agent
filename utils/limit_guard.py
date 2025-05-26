import csv
import os
from datetime import datetime
from datetime import date

LOG_FILE = "data/tweet_log.csv"
MAX_DAILY_TWEETS = 17  # You can change this based on your tier

def has_reached_daily_limit():
    if not os.path.exists(LOG_FILE):
        return False

    today = date.today().isoformat()
    count = 0
    with open(LOG_FILE, newline='', encoding='utf-8') as csvfile:
         for row in csv.DictReader(csvfile):
             row_date = row.get('date') or row.get('timestamp')
             if row_date == today:
                 count += 1
    return count >= MAX_DAILY_TWEETS