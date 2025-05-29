"""
GPT-based scoring for headlines.
Logs scores to CSV and Notion.
"""

import csv
import logging
import os
from datetime import datetime

from .config import DATA_DIR, LOG_DIR
from .gpt import client
from .notion_logger import log_headline as notion_log_headline

# Setup logging to file
log_file = os.path.join(LOG_DIR, "scorer.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# CSV file to record all scored headlines
SCORED_CSV = os.path.join(DATA_DIR, "all_scored_headlines.csv")


def score_headline(text: str) -> float:
    """
    Score a single headline and return its float score.
    """
    records = score_headlines([{"headline": text, "url": ""}])
    return records[0]["score"] if records else 0.0


def score_headlines(items: list[dict]) -> list[dict]:
    """
    items: list of {'headline': str, 'url': str}
    Returns list of dicts with 'headline', 'url', 'score', 'timestamp'
    """
    results = []
    for item in items:
        # Formulate prompt for scoring
        prompt = (
            f"Score this crypto news headline from 1 to 10 based on how likely it is to go viral on Twitter: "
            f"'{item['headline']}'"
        )
        # Get completion from GPT client
        response = client.complete(prompt)
        try:
            score = float(response.strip())
        except Exception:
            score = 0.0

        record = {
            "headline": item["headline"],
            "url": item["url"],
            "score": score,
            "timestamp": datetime.utcnow().isoformat(),
        }
        # Log to CSV and Notion
        _append_to_csv(record)
        notion_log_headline(record)
        logging.info(f"Scored headline: '{item['headline']}' -> {score}")
        results.append(record)

    return results


def _append_to_csv(record: dict):
    """
    Append a scored record to the CSV file.
    """
    header = ["headline", "url", "score", "timestamp"]
    exists = os.path.exists(SCORED_CSV)
    with open(SCORED_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not exists:
            writer.writeheader()
        writer.writerow(record)


def write_headlines(records: list[dict]):
    """
    Convenience function to write multiple scored records at once.
    """
    for rec in records:
        _append_to_csv(rec)
        notion_log_headline(rec)
