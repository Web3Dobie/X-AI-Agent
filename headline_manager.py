
import csv
import logging
from datetime import datetime
from news_fetcher import fetch_headlines, extract_ticker_from_headline
from gpt_helpers import client as gpt_client
from notion_logger import log_headline
import os

def ingest_and_score_headlines():
    headlines = fetch_headlines(limit=5)
    timestamp = datetime.utcnow().isoformat()
    scored = []

    for title, url in headlines:
        if headline_already_used_today(title):
            logging.info(f"⏩ Skipping duplicate headline (already scored today): {title}")
            continue

        prompt = (
            f"Rate the following crypto headline from 1 to 10 for potential to go viral on X (Twitter), "
            f"based on novelty, controversy, clarity, and emotional pull. Just return a number.\n\n"
            f"Headline: {title}"
        )
        try:
            response = gpt_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a viral content strategist for Crypto Twitter."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=5,
                temperature=0.7
            )
            score = round(float(response.choices[0].message.content.strip()))
            ticker = extract_ticker_from_headline(title)
            scored.append((score, title, url, ticker, timestamp))

            # Notion logging
            log_headline(
                date_ingested=timestamp,
                headline=title,
                relevance=score,
                viral_score=score,  # for now use same score
                used=False,
                source_url=url
            )

        except Exception as e:
            logging.warning(f"⚠️ Failed to score headline: {title} — {e}")
            continue

    if scored:
        with open("logs/scored_headlines.csv", mode="a", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(["score", "headline", "url", "ticker", "timestamp"])
            for row in scored:
                writer.writerow(row)
        logging.info(f"✅ Stored {len(scored)} scored headlines.")

def get_top_headline():
    today = datetime.utcnow().date().isoformat()
    try:
        with open("logs/scored_headlines.csv", newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            sorted_rows = sorted(
                (r for r in reader if r["timestamp"].startswith(today)),
                key=lambda r: int(r["score"]),
                reverse=True
            )
            for row in sorted_rows:
                return row["headline"], row["url"], row["ticker"]
    except Exception as e:
        logging.error(f"❌ Error reading scored headlines: {e}")
    return None, None, None

def headline_already_used_today(headline_text):
    today = datetime.utcnow().date().isoformat()
    try:
        with open("logs/scored_headlines.csv", newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return any(
                row["headline"].strip().lower() == headline_text.strip().lower()
                and row["timestamp"].startswith(today)
                for row in reader
            )
    except FileNotFoundError:
        return False
