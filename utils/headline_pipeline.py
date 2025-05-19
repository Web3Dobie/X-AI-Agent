import os
import csv
import logging
from datetime import datetime
from utils.scorer import score_headlines
from utils.rss_fetch import fetch_headlines

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/activity.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

def fetch_and_score_headlines():
    logging.info("📥 Starting headline ingestion and scoring...")
    headlines = fetch_headlines(limit=25)
    logging.info(f"🔎 Fetched {len(headlines)} headlines.")

    seen = set()
    if os.path.exists("data/scored_headlines.csv"):
        with open("data/scored_headlines.csv", newline="", encoding="utf-8") as f:
            seen = {row["headline"] for row in csv.DictReader(f)}

    new_headlines = [h for h in headlines if h["headline"] not in seen]
    if not new_headlines:
        logging.info("⏭ No new headlines to score.")
        return

    logging.info(f"🧠 Scoring {len(new_headlines)} new headlines with GPT...")
    score_headlines(new_headlines)

    with open("data/scored_headlines.csv", "a", newline="", encoding="utf-8") as f:
           writer = csv.DictWriter(f, fieldnames=["score", "headline", "url", "ticker", "timestamp"])
           if f.tell() == 0:
            writer.writeheader()
            writer.writerow({
                "score": score,
                "headline": headline["headline"],
                "url": headline["url"],
                "ticker": headline.get("ticker", "CRYPTO"),
                "timestamp": datetime.utcnow().isoformat()
            })


def get_top_headline_last_7_days():
    """Return the highest-scoring headline from the last 7 days."""
    try:
        with open("data/scored_headlines.csv", newline="", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
    except FileNotFoundError:
        logging.warning("⚠️ No scored headlines file found.")
        return None

    one_week_ago = datetime.utcnow().timestamp() - (7 * 86400)
    filtered = [
        row for row in reader
        if float(row["score"]) > 0 and datetime.fromisoformat(row["timestamp"]).timestamp() >= one_week_ago
    ]

    if not filtered:
        logging.info("❌ No headlines from past 7 days found.")
        return None

    top = max(filtered, key=lambda x: float(x["score"]))
    return {
        "headline": top["headline"],
        "url": top["url"]
    }
