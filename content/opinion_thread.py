import logging
import csv
from datetime import datetime
import string
from utils.gpt import generate_gpt_thread
from utils.x_post import post_thread

def get_top_headline():
    today = datetime.utcnow().date()
    try:
        with open("data/scored_headlines.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headlines = [
                row for row in reader
                if datetime.fromisoformat(row["timestamp"]).date() == today
            ]
    except Exception as e:
        logging.error(f"❌ Error reading scored headlines: {e}")
        return None, None

    if not headlines:
        logging.warning("⚠️ No headlines found for today.")
        return None, None

    valid_headlines = []
    for h in headlines:
        try:
            h["score"] = float(h["score"])
            valid_headlines.append(h)
        except Exception:
            logging.warning(f"⚠️ Skipped malformed headline: {h}")

    if not valid_headlines:
        logging.warning("❌ No valid headlines found for today.")
        return None, None

    top = max(valid_headlines, key=lambda h: h["score"])

    return top["headline"], top["url"]

def generate_top_news_opinion():
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
        return []

    date = datetime.utcnow().strftime("%Y-%m-%d")
    thread_parts[0] = f"🔥 Hunter Reacts [{date}]\n" + thread_parts[0]

    # Remove existing sign-off if GPT added it anyway
    thread_parts[-1] = thread_parts[-1].replace("— Hunter 🐾", "").strip()

    # Now safely append our own sign-off
    thread_parts[-1] += f"\n— Hunter 🐾\n🔗 {url}"

    return thread_parts

def post_top_news_thread():
    try:
        thread_parts = generate_top_news_opinion()
        if thread_parts:
            post_thread(thread_parts, category="news_opinion")
    except Exception as e:
        logging.error(f"❌ Error generating or posting top news thread: {e}")