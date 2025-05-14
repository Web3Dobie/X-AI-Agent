
import csv
import os
from datetime import datetime, timedelta
from notion_logger import log_weekly_report

def generate_weekly_report():
    tweet_data = {}
    report = []

    try:
        with open("logs/tweet_log.csv", newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tweet_id = row["tweet_id"]
                timestamp = datetime.fromisoformat(row["timestamp"])
                if timestamp.date() >= (datetime.utcnow().date() - timedelta(days=7)):
                    tweet_data[tweet_id] = {
                        "tweet_id": tweet_id,
                        "content": row["content"][:100],
                        "type": row["category"],
                        "timestamp": row["timestamp"],
                        "likes": 0,
                        "retweets": 0,
                        "replies": 0,
                        "url": f"https://x.com/{USERNAME}/status/{tweet_id}"
                    }
    except FileNotFoundError:
        print("❌ tweet_log.csv not found.")
        return

    try:
        with open("logs/performance_log.csv", newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tweet_id = row["tweet_id"]
                if tweet_id in tweet_data:
                    tweet_data[tweet_id]["likes"] = int(row["likes"])
                    tweet_data[tweet_id]["retweets"] = int(row["retweets"])
                    tweet_data[tweet_id]["replies"] = int(row["replies"])
    except FileNotFoundError:
        print("⚠️ performance_log.csv not found. Will include tweet metadata only.")

    for entry in tweet_data.values():
        engagement_score = entry["likes"] + entry["retweets"] + entry["replies"]
        entry["engagement_score"] = engagement_score
        report.append(entry)

    report.sort(key=lambda x: x["engagement_score"], reverse=True)

    # Generate the weekly report thread
    top_3 = [r["tweet_id"] for r in report[:3]]
    follower_growth = 0  # Replace with actual count if tracked elsewhere
    summary = f"Top tweets: {', '.join(top_3)}\nEntries: {len(report)}"

    log_weekly_report(
        week_ending=datetime.utcnow().date().isoformat(),
        follower_growth=follower_growth,
        top_tweets="\n".join(top_3),
        summary=summary
    )

    print(f"✅ Weekly report written.")
