import logging
import os
import re
from datetime import datetime
from utils.gpt import generate_gpt_text
from utils.headline_pipeline import get_top_headline_last_7_days  # ✅ Use shared logic
from utils.notion_helpers import log_substack_post_to_notion  # ✅ import

def slugify(text):
    return re.sub(r'\W+', '-', text.lower()).strip('-')

def generate_substack_explainer():
    logging.basicConfig(filename='logs/activity.log', level=logging.INFO, format='%(asctime)s - %(message)s')
    logging.info("📘 Generating Substack explainer post")

    headline = get_top_headline_last_7_days()
    if not headline:
        logging.info("⏭ No headlines available for explainer generation")
        return None

    topic = headline['headline']
    url = headline['url']
    date = datetime.utcnow().strftime("%B %d, %Y")

    prompt = f"""
You're Hunter 🐾 — a witty Doberman who explains complex crypto topics in plain English with personality and insight.

Write an 800–1,000 word Substack article about:
"{topic}"

Use this format:
- Title
- TL;DR (3 bullets)
- What's the deal?
- Why does it matter?
- Hunter's take
- Bottom line

Inject emojis, sass, and clarity. Wrap with a reminder to follow @Web3_Dobie and link to: {url}
Today is {date}.
"""

    article = generate_gpt_text(prompt, max_tokens=1800)
    if not article:
        logging.warning("⚠️ GPT returned no content for Substack post")
        return None

    logging.info("✅ Substack post generated")

    # ✅ Save locally
    os.makedirs("substack_posts", exist_ok=True)
    filename = f"substack_posts/{datetime.utcnow().strftime('%Y-%m-%d')}_{slugify(topic)}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(article)

    logging.info(f"📝 Article saved locally at {filename}")

    # ✅ Log to Notion
    log_substack_post_to_notion(topic, filename)

    return {
        "content": article,
        "filename": filename,
        "headline": topic
    }