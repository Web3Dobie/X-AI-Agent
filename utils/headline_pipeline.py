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
    scored = score_headlines(new_headlines)

    for headline, score in zip(new_headlines, scored):
        logging.info(f"🧠 Scored: {headline['headline']} — {score}")
        logging.info(f"📤 Storing scored headline: {headline['headline']}")

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

    logging.info(f"✅ Stored {len(scored)} scored headlines.")