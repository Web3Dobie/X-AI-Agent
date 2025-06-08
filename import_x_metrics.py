import csv
import os
from datetime import datetime

TWEET_LOG_FILE = "data/tweet_log.csv"
EXPORT_FILE = None  # Leave as None to auto-detect the latest export
OUTPUT_FILE = "data/tweet_metrics_enriched.csv"
EXPORT_FOLDER = "data"


def detect_latest_x_export():
    files = [
        f
        for f in os.listdir(EXPORT_FOLDER)
        if f.startswith("account_analytics_content") and f.endswith(".csv")
    ]
    if not files:
        raise FileNotFoundError("❌ No X analytics export file found in /data/")
    latest = max(files, key=lambda f: os.path.getctime(os.path.join(EXPORT_FOLDER, f)))
    return os.path.join(EXPORT_FOLDER, latest)


def load_csv_dict(filepath, key_field):
    with open(filepath, newline="", encoding="utf-8") as f:
        return {row[key_field]: row for row in csv.DictReader(f)}


def import_metrics():
    export_path = EXPORT_FILE or detect_latest_x_export()
    print(f"📥 Using X export file: {export_path}")

    tweet_log = load_csv_dict(TWEET_LOG_FILE, key_field="tweet_id")
    print("tweet_log keys (first 5):", list(tweet_log.keys())[:5])

    with open(export_path, newline="", encoding="utf-8") as f:
        export = list(csv.DictReader(f))
    export_ids = [str(row.get("Post id", "")).strip().split(".")[0] for row in export]
    print("export tweet_ids (first 5):", export_ids[:5])

    enriched_rows = []
    # filepath: /home/Hunter/X-AI-Agent/import_x_metrics.py
    for row in export:
        tweet_id = str(row.get("Post id", "")).strip().split(".")[0]
        if tweet_id not in tweet_log:
            print(f"Not found in tweet_log: '{tweet_id}'")
            continue

        base = tweet_log[tweet_id]
        try:
            likes = int(row.get("Likes", 0))
            retweets = int(row.get("Retweets", 0))
            replies = int(row.get("Replies", 0))
            impressions = int(row.get("Impressions", 0))

            engagement_score = (
                likes * 1 + retweets * 2 + replies * 1.5 + impressions * 0.01
            )

            enriched_rows.append(
                {
                    "tweet_id": tweet_id,
                    "date": base["timestamp"],
                    "type": base["type"],
                    "url": base["category"],
                    "likes": likes,
                    "retweets": retweets,
                    "replies": replies,
                    "impressions": impressions,
                    "engagement_score": round(engagement_score, 2),
                }
            )
        except Exception as e:
            print(f"⚠️ Skipping tweet {tweet_id}: {e}")

    if not enriched_rows:
        print("❌ No tweets matched between log and export.")
        return

    # ✅ Sort by engagement score descending
    enriched_rows.sort(key=lambda r: float(r["engagement_score"]), reverse=True)

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=enriched_rows[0].keys())
        writer.writeheader()
        writer.writerows(enriched_rows)

    print(f"✅ Wrote enriched metrics to: {OUTPUT_FILE}")


if __name__ == "__main__":
    import_metrics()
