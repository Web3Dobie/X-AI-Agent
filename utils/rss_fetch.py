"""
Fetch RSS news headlines, filter out seen ones, and log them.
Appends new headlines to HEADLINE_LOG in DATA_DIR.
"""

import csv
import logging
import os
from datetime import datetime

import feedparser

from .config import DATA_DIR, LOG_DIR

# Configure logging
log_file = os.path.join(LOG_DIR, "rss_fetch.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
    "https://cryptoslate.com/feed/",
    "https://www.beincrypto.com/feed/",
    "https://cointelegraph.com/rss",
]

HEADLINE_LOG = os.path.join(DATA_DIR, "scored_headlines.csv")


def fetch_headlines(limit=10):
    """
    Fetch up to 'limit' new headlines from configured RSS_FEEDS,
    skipping any already present in HEADLINE_LOG.
    Returns a list of dicts: {"headline": title, "url": link}.
    """
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    seen = set()
    if os.path.exists(HEADLINE_LOG):
        with open(HEADLINE_LOG, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(
                csvfile, fieldnames=["headline", "url", "score", "timestamp"]
            )
            for row in reader:
                seen.add(row["headline"])

    headlines = []
    try:
        for url in RSS_FEEDS:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.title.strip()
                link = entry.link.strip()
                if title not in seen and title not in [
                    h["headline"] for h in headlines
                ]:
                    headlines.append({"headline": title, "url": link})
                    logging.info(f"📰 New headline fetched: {title}")
                if len(headlines) >= limit:
                    break
            if len(headlines) >= limit:
                break
    except Exception as e:
        logging.error(f"❌ Error fetching RSS feeds: {e}")

    return headlines
