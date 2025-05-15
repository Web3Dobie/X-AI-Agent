from utils.rss_fetch import fetch_headlines
from utils.scorer import score_headlines
import logging

def fetch_and_score_headlines():
    logging.info("🗞️ Fetching and scoring headlines...")
    headlines = fetch_headlines(limit=10)
    if headlines:
        score_headlines(headlines)
        logging.info(f"✅ Stored {len(headlines)} scored headlines.")
    else:
        logging.info("💤 No new headlines to score.")