import csv
from collections import Counter
from datetime import datetime

def report_tweet_volume():
    try:
        with open("logs/tweet_log.csv", newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            dates = [datetime.fromisoformat(row["timestamp"]).date().isoformat() for row in reader]
            counter = Counter(dates)

        print("📊 Tweet Volume by Date:")
        for date, count in sorted(counter.items()):
            print(f"{date}: {count} tweets")
    except FileNotFoundError:
        print("❌ tweet_log.csv not found.")