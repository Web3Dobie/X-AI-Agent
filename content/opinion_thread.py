"""
Generate and post a 3-part "Hunter Reacts" thread on X for the top headline of the day.
"""

import csv
import logging
import os
from datetime import datetime

import requests

from utils import (DATA_DIR, LOG_DIR, generate_gpt_thread, insert_cashtags,
                   insert_mentions, post_thread)

# Configure logging
log_file = os.path.join(LOG_DIR, "opinion_thread.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def get_top_headline():
    """
    Return the highest-scoring headline and URL from today's scored_headlines.csv.
    """
    today = datetime.utcnow().date()
    path = os.path.join(DATA_DIR, "scored_headlines.csv")
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headlines = [
                row
                for row in reader
                if datetime.fromisoformat(row["timestamp"]).date() == today
            ]
    except Exception as e:
        logging.error(f"❌ Error reading scored headlines: {e}")
        return None, None

    if not headlines:
        logging.warning("⚠️ No headlines found for today.")
        return None, None

    valid = []
    for h in headlines:
        try:
            h["score"] = float(h["score"])
            valid.append(h)
        except Exception:
            logging.warning(f"⚠️ Skipped malformed headline: {h}")

    if not valid:
        logging.warning("❌ No valid headlines found for today.")
        return None, None

    top = max(valid, key=lambda h: h["score"])
    return top["headline"], top["url"]


def is_valid_url(url: str) -> bool:
    """
    Check if the URL returns status 200.
    """
    try:
        resp = requests.head(url, allow_redirects=True, timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def generate_top_news_opinion():
    """
    Generate a 3-part reaction thread to today's top crypto headline.
    """
    headline, url = get_top_headline()
    if not headline:
        return []

    prompt = f"""
Write a 3-part tweet thread reacting to this crypto headline with bold, clever, Web3-native commentary.
Use emojis, snark, and wit. Don't sign off with ' Hunter 🐾'. Use relevant hashtags. Separate tweets with '---'.

Headline:
{headline}
"""

    thread_parts = generate_gpt_thread(prompt, max_parts=3, delimiter="---")
    if not thread_parts or len(thread_parts) < 3:
        logging.warning("⚠️ GPT returned insufficient parts.")
        return []

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    thread_parts[0] = f"🔥 Hunter Reacts [{date_str}]\n\n" + thread_parts[0]
    # Remove any accidental sign-offs
    thread_parts[-1] = thread_parts[-1].replace("— Hunter 🐾", "").strip()

    # Append URL if valid
    if url and is_valid_url(url):
        logging.info(f"📌 reacting to headline: {headline} — {url}")
        thread_parts[-1] += f"— Hunter 🐾 🔗 {url}"
    else:
        logging.warning(f"⚠️ Skipping broken or missing URL for headline: {headline}")
        thread_parts[-1] += "— Hunter 🐾"

    return thread_parts


def post_top_news_thread():
    """
    Fetch, generate, and post the opinion thread on X.
    """
    try:
        parts = generate_top_news_opinion()
        if parts:
            parts = [insert_cashtags(insert_mentions(p)) for p in parts]
            post_thread(parts, category="news_opinion")
            logging.info("✅ Opinion thread posted")
        else:
            logging.info("⏭ No opinion thread to post")
    except Exception as e:
        logging.error(f"❌ Error in opinion thread pipeline: {e}")
