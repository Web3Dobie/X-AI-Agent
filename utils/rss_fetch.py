import feedparser
from datetime import datetime
import os
import csv

RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
    "https://cryptoslate.com/feed/",
    "https://www.beincrypto.com/feed/",
    "https://cointelegraph.com/rss"
]

HEADLINE_LOG = "data/scored_headlines.csv"

def fetch_headlines(limit=10):
    seen = set()
    if os.path.exists(HEADLINE_LOG):
        with open(HEADLINE_LOG, newline='', encoding='utf-8') as csvfile:
            for row in csv.DictReader(csvfile):
                seen.add(row['headline'])

    headlines = []
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.title.strip()
            link = entry.link.strip()
            if title not in seen and title not in [h['headline'] for h in headlines]:
                headlines.append({"headline": title, "url": link})
            if len(headlines) >= limit:
                break
        if len(headlines) >= limit:
            break
    return headlines