import logging
import os
import re
from datetime import datetime

from utils import (LOG_DIR, SUBSTACK_POST_DIR, generate_gpt_text,
                   get_top_headline_last_7_days, log_substack_post_to_notion)

# ─── Configure a module‐specific logger ──────────────────────────────────

log_file = os.path.join(LOG_DIR, "explainer_writer.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)

# 1) Get (or create) a logger named “explainer_writer”
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 2) Create a FileHandler that writes ONLY to explainer_writer.log
fh = logging.FileHandler(log_file, encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
fh.setFormatter(formatter)
logger.addHandler(fh)

# 3) (Optional) If you also want console output, add a StreamHandler:
#    ch = logging.StreamHandler()
#    ch.setFormatter(formatter)
#    logger.addHandler(ch)

# Now, every time you write `logger.info(...)` / `logger.error(...)`, it
# will go into explainer_writer.log, regardless of what the root logger
# is doing.
# ───────────────────────────────────────────────────────────────────────


def slugify(text: str) -> str:
    """
    Create a URL-friendly slug from the given text.
    """
    return re.sub(r"\W+", "-", text.lower()).strip("-")


def generate_substack_explainer():
    """
    Build an 800–1,000 word Substack article on the top weekly headline.
    Saves the article markdown to SUBSTACK_POST_DIR and logs to Notion.
    Returns a dict with keys: 'headline', 'content', 'filename'.
    """
    logger.info("📘 Generating Substack explainer post")

    # Fetch top headline
    headline_entry = get_top_headline_last_7_days()
    if not headline_entry:
        logger.info("⏭ No headlines available for explainer generation")
        return None

    topic = headline_entry["headline"]
    url = headline_entry["url"]
    date_str = datetime.utcnow().strftime("%B %d, %Y")

    prompt = f"""
You're Hunter 🐾 — a witty Doberman who explains complex crypto topics in plain English with personality and insight.

Write an 1,000–1,500 word Substack article about:
"{topic}"

Use this format:
- Title
- Subtitle "Don't worry: Hunter Explains 🐾"
- TL;DR (3 bullets)
- What's the deal?
- Why does it matter?
- Hunter's take
- Bottom line

Inject emojis, sass, and clarity. Wrap with a reminder to follow @Web3_Dobie and link to: {url}
Today is {date_str}.
"""
    article = generate_gpt_text(prompt, max_tokens=1800)
    if not article:
        logger.warning("⚠️ GPT returned no content for Substack post")
        return None

    logger.info("✅ Substack post generated")

    # Save locally to SUBSTACK_POST_DIR
    os.makedirs(SUBSTACK_POST_DIR, exist_ok=True)
    slug = slugify(topic)
    filename = f"{datetime.utcnow().strftime('%Y-%m-%d')}_{slug}.md"
    filepath = os.path.join(SUBSTACK_POST_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(article)
    logger.info(f"📝 Article saved locally at {filepath}")

    # Log to Notion
    try:
        log_substack_post_to_notion(topic, filepath)
        logger.info("✅ Logged Substack post to Notion")
    except Exception as e:
        logger.error(f"❌ Notion logging failed: {e}")

    return {"headline": topic, "content": article, "filename": filepath}
