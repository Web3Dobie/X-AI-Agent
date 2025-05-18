import logging
import csv
from datetime import datetime
from utils.gpt import generate_gpt_thread
from utils.x_post import post_thread
from utils.text_utils import insert_cashtags, insert_mentions

def get_today_headlines():
    today = datetime.utcnow().date()
    headlines = []
    try:
        with open("data/scored_headlines.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = datetime.fromisoformat(row["timestamp"]).date()
                if ts == today:
                    headlines.append(row)
    except Exception as e:
        logging.error(f"❌ Error reading scored_headlines.csv: {e}")
    return headlines

def generate_summary_thread():
    headlines = get_today_headlines()
    if not headlines or len(headlines) < 3:
        logging.warning("⚠️ Not enough fresh headlines for news thread.")
        return []

    valid_headlines = []
    for h in headlines:
        try:
            h["score"] = float(h["score"])
            valid_headlines.append(h)
        except (ValueError, TypeError):
            logging.warning(f"⚠️ Skipped malformed headline during sorting: {h}")

    top3 = sorted(valid_headlines, key=lambda h: h["score"], reverse=True)[:3]


    prompt = "\n".join([f"{h['headline']}" for h in top3])
    full_prompt = f"""
Write 3 engaging tweets summarizing today's top crypto headlines. Be clever, use emojis, and close each with '— Hunter 🐾'.
Separate tweets using '---'. Do not include numbers or headers.

{prompt}
"""

    thread_parts = generate_gpt_thread(full_prompt, max_parts=3, delimiter="---")
    if not thread_parts or len(thread_parts) < 3:
        return []

    date = datetime.utcnow().strftime("%Y-%m-%d")
    thread_parts[0] = f"Daily Dobie Headlines [{date}] 📰\n\n" + thread_parts[0]
    return thread_parts

def post_news_thread():
    thread_parts = generate_summary_thread()
    if thread_parts:
        thread_parts = [insert_cashtags(part) for part in thread_parts]
        thread_parts = [insert_mentions(part) for part in thread_parts]
        post_thread(thread_parts, category="news_summary")