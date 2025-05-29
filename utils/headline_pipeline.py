"""
Pipeline to fetch, score, and select top headlines using RSS and GPT-based scoring.
Logs and data paths are centralized in utils.config.
"""

import csv
import logging
import os
from datetime import datetime, timedelta

from .config import DATA_DIR, LOG_DIR
from .rss_fetch import fetch_headlines
from .scorer import score_headline

# Setup logging
log_file = os.path.join(LOG_DIR, "headline_pipeline.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

SCORED_FILE = os.path.join(DATA_DIR, "scored_headlines.csv")


def fetch_and_score_headlines(limit=25):
    """
    Fetch new headlines via RSS, score them, and append to SCORED_FILE.
    """
    logging.info("📥 Starting headline ingestion and scoring...")
    # Fetch headlines (returns list of dicts with 'headline', 'url')
    headlines = fetch_headlines(limit=limit)
    logging.info(f"🔎 Fetched {len(headlines)} headlines.")

    # Load seen headlines
    seen = set()
    if os.path.exists(SCORED_FILE):
        with open(SCORED_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            seen = {row["headline"] for row in reader}

    # Filter new
    new = [h for h in headlines if h["headline"] not in seen]
    if not new:
        logging.info("⏭ No new headlines to score.")
        return

    # Score and append
    with open(SCORED_FILE, "a", newline="", encoding="utf-8") as f:
        fieldnames = ["headline", "url", "score", "timestamp"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if f.tell() == 0:
            writer.writeheader()
        for h in new:
            score = score_headline(h["headline"])
            writer.writerow(
                {
                    "headline": h["headline"],
                    "url": h["url"],
                    "score": score,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
    logging.info(f"✅ Scored and recorded {len(new)} headlines.")


def get_top_headline_last_7_days():
    """
    Return the highest-scoring headline from the last 7 days.
    """
    try:
        with open(SCORED_FILE, newline="", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
    except FileNotFoundError:
        logging.warning("⚠️ No scored headlines file found.")
        return None

    one_week_ago = datetime.utcnow() - timedelta(days=7)
    recent = [
        row
        for row in reader
        if datetime.fromisoformat(row["timestamp"]) >= one_week_ago
    ]
    if not recent:
        logging.info("❌ No headlines from past 7 days found.")
        return None

    top = max(recent, key=lambda x: float(x["score"]))
    return {"headline": top["headline"], "url": top["url"]}
