"""
Generate and post a daily news recap thread on X summarizing the top crypto headlines.
"""

import csv
import logging
import os
from datetime import datetime

from utils import (DATA_DIR, LOG_DIR, generate_gpt_thread, insert_cashtags,
                   insert_mentions, post_thread, get_module_logger)

logger = get_module_logger(__name__)


HEADLINE_LOG = os.path.join(DATA_DIR, "scored_headlines.csv")


def get_today_headlines():
    """
    Read today's scored headlines from HEADLINE_LOG and return as list of dicts.
    """
    today = datetime.utcnow().date()
    headlines = []
    try:
        with open(HEADLINE_LOG, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = datetime.fromisoformat(row["timestamp"]).date()
                if ts == today:
                    headlines.append(row)
    except Exception as e:
        logger.error(f"❌ Error reading {HEADLINE_LOG}: {e}")
    return headlines


def generate_summary_thread():
    """
    Build a 3-part GPT thread summarizing today's top crypto headlines.
    """
    headlines = get_today_headlines()
    if not headlines or len(headlines) < 3:
        logger.warning("⚠️ Not enough fresh headlines for news thread.")
        return []

    # Validate and sort by score
    valid = []
    for h in headlines:
        try:
            h["score"] = float(h["score"])
            valid.append(h)
        except (ValueError, TypeError):
            logger.warning(f"⚠️ Skipped malformed headline during sorting: {h}")
    top3 = sorted(valid, key=lambda h: h["score"], reverse=True)[:3]

    # Build GPT prompt
    prompt_lines = [h["headline"] for h in top3]
    prompt = "Write 3 engaging tweets summarizing today's top crypto headlines. Be clever, use emojis, and close each with '— Hunter 🐾'. Separate tweets using '---'. Do not include numbers or headers.\n\n"
    prompt += "\n".join(prompt_lines)

    thread_parts = generate_gpt_thread(prompt, max_parts=3, delimiter="---")
    if not thread_parts or len(thread_parts) < 3:
        logger.warning("⚠️ GPT returned insufficient parts for news recap.")
        return []

    # Prepend header and apply cashtags/mentions
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    header = f"Daily Dobie Headlines [{date_str}] 📰\n\n"
    thread_parts[0] = header + thread_parts[0]
    thread_parts = [insert_mentions(insert_cashtags(p)) for p in thread_parts]
    return thread_parts


def post_news_thread():
    """
    Generate and post the news recap thread on X.
    """
    logger.info("🔄 Starting daily news recap thread")
    thread = generate_summary_thread()
    if thread:
        post_thread(thread, category="news_summary")
        logger.info("✅ News recap thread posted")
    else:
        logger.info("⏭ No news recap thread posted")
