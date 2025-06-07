"""
GPT-based scoring for headlines.
Logs scores to CSV and Notion.
"""
import csv
import logging
import os
from datetime import datetime

from .config import DATA_DIR, LOG_DIR
from .gpt import generate_gpt_text
from .notion_logger import log_headline_to_vault as notion_log_headline
from .text_utils import extract_ticker

# Configure logging
log_file = os.path.join(LOG_DIR, "scorer.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# CSV file to record all scored headlines
SCORED_CSV = os.path.join(DATA_DIR, "scored_headlines.csv")


def score_headline(text: str, url: str = "", ticker: str = "") -> float:
    """
    Score a single headline and return its float score.
    """
    records = score_headlines([{"headline": text, "url": url, "ticker": ticker}])
    return records[0]["score"] if records else 0.0


def score_headlines(items: list[dict]) -> list[dict]:
    """
    items: list of {'headline': str, 'url': str, 'ticker': str (optional)}
    Returns list of dicts with 'headline', 'url', 'ticker', 'score', 'timestamp'
    """
    results = []
    for item in items:
        headline = item.get("headline", "")
        url = item.get("url", "")
        ticker = item.get("ticker", "")

        # If pipeline didnt supply a ticker, backfill:
        if not ticker:
            ticker = extract_ticker(headline)

        # Formulate prompt (explicitly mention ticker)
        prompt = (
            f"Score this news headline about {ticker} from 1 to 10, based on how likely it is to go viral on Twitter: "
            f"\"{headline}\""
        )
        response = generate_gpt_text(prompt)
        
        # Try parsing response as float, then round to nearest int (clamp to [1..10])
        try:
             raw = float(response.strip())
             score = int(round(raw))
        except Exception:
             score = 1

        if score < 1:
            score = 1
        elif score > 10:
            score = 10

        timestamp = datetime.utcnow().isoformat()
        record = {
            "headline": headline,
            "url":       url,
            "ticker":    ticker,
            "score":     score,
            "timestamp": timestamp,
        }

        # Append to CSV and log to Notion
        _append_to_csv(record)
        notion_log_headline(
            date_ingested=timestamp,
            headline=headline,
            relevance_score=score,
            viral_score=score,
            used=False,
            source_url=url,
        )

        logging.info(f"Scored headline: '{headline}' -> {score}")
        results.append(record)

    return results


def _append_to_csv(record: dict):
    """
    Append a scored record to the CSV file with standardized header.
    """
    header = ["score", "headline", "url", "ticker", "timestamp"]
    os.makedirs(DATA_DIR, exist_ok=True)
    write_header = not os.path.exists(SCORED_CSV)
    with open(SCORED_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if write_header:
            writer.writeheader()
        # Ensure all fields are present
        row = {
            "score": record.get("score", 0),
            "headline": record.get("headline", ""),
            "url": record.get("url", ""),
            "ticker": record.get("ticker", ""),
            "timestamp": record.get("timestamp", ""),
        }
        writer.writerow(row)


def write_headlines(records: list[dict]):
    """
    Convenience function to write multiple scored records at once.
    """
    for rec in records:
        # Ensure required keys
        rec.setdefault("url", "")
        rec.setdefault("ticker", "")
        rec.setdefault("timestamp", datetime.utcnow().isoformat())
        _append_to_csv(rec)
        notion_log_headline(
            date_ingested=rec["timestamp"],
            headline=rec["headline"],
            relevance_score=rec["score"],
            viral_score=rec["score"],
            used=False,
            source_url=rec["url"],
        )
