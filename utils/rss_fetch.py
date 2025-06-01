"""
Fetch RSS news headlines, filter out seen ones, and log them.
Appends new headlines to HEADLINE_LOG in DATA_DIR.
"""

import csv
import logging
import os
from datetime import datetime

import feedparser

from .config import DATA_DIR, LOG_DIR, RSS_FEED_URLS

# Configure logging
log_file = os.path.join(LOG_DIR, "rss_fetch.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# RSS_FEEDS = [
#    "https://www.coindesk.com/arc/outboundfeeds/rss/",
#    "https://decrypt.co/feed",
#    "https://cryptoslate.com/feed/",
#    "https://www.beincrypto.com/feed/",
#    "https://cointelegraph.com/rss",
#]

RSS_FEED_URLS=RSS_FEED_URLS

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
            reader = csv.DictReader(csvfile)
            for row in reader:
                # If the CSV was written by scorer.py, 'headline' is one of its actual column names
                if "headline" in row:
                    seen.add(row["headline"])

    headlines = []
    try:
        for source_name, url in RSS_FEED_URLS.items():
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.title.strip()
                link = entry.link.strip()
                # Only keep it if we haven't seen it before, or already queued just now in this batch
                if title not in seen and title not in [h["headline"] for h in headlines]:
                   headlines.append({"headline": title, "url": link})
                   logging.info(f"New headline fetched from {source_name}: {title}")
                if len(headlines) >= limit:
                    break
            if len(headlines) >= limit:
                break
    except Exception as e:
        logging.error(f"[ERROR] Error fetching RSS feeds: {e}")

    return headlines
