# explainer.py

"""
Generates and posts a 3-part "Hunter Explains" thread on X for the top weekly headline.
Minimal fix that just removes substack URL dependency.
"""

import logging
from datetime import datetime
import os

from utils import (
    LOG_DIR,
    generate_gpt_thread,
    get_top_headline_last_7_days,
    post_thread, upload_media,
)

# ─── Configure a module-specific logger for explainer ───────────────────
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Only add one FileHandler even if this module is re-imported
if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    log_file = os.path.join(LOG_DIR, "explainer.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
# ────────────────────────────────────────────────────────────────────────────


def post_dobie_explainer_thread():
    """
    Generate and publish explainer article, then post thread on X.
    Fixed version that removes substack_url dependency.
    """
    logger.info("🧵 Starting Dobie explainer thread generation")

    try:
        # 1) Generate the explainer article first
        from content.explainer_writer import generate_substack_explainer
        
        logger.info("📝 Generating explainer article...")
        result = generate_substack_explainer()
        
        if not result:
            logger.error("❌ Explainer article generation failed")
            raise Exception("Explainer article generation failed")
        
        # Extract the article URL from the result
        article_url = result.get('article_url', '')
        headline = result.get('headline', 'Weekly Explainer')
        
        logger.info(f"✅ Explainer article published: {headline}")
        
        # 2) Grab last week's top headline for the thread
        headline_entry = get_top_headline_last_7_days()
        if not headline_entry:
            logger.warning("❌ No headline found for explainer thread; but article was published")
            return  # Don't fail the whole job - article was published successfully

        topic = headline_entry["headline"]
        source_url = headline_entry["url"]
        today_str = datetime.utcnow().strftime("%Y-%m-%d")

        # 3) Build a prompt that asks for a 3-part thread
        prompt = f"""
Write a 3-part Twitter thread called 'Hunter Explains' about:
\"{topic}\"

Make it simple, clever, and accessible for casual readers. Add emojis and bold takes.
Each tweet must be <280 characters and end with '— Hunter 🐾'.
(Do NOT include the header "Hunter Explains 🧵 [date]" or article links in the tweets themselves—those will be added manually.)
"""

        thread = generate_gpt_thread(prompt, max_parts=3)
        if not thread:
            logger.warning("⚠️ GPT returned no content for explainer thread; but article was published")
            return  # Don't fail - article was published

        # 4) Prepend exactly one "Hunter Explains 🧵 [YYYY-MM-DD]" header + blank line to the first tweet
        header = f"Hunter Explains 🧵 [{today_str}]\n\n"
        thread[0] = header + thread[0].lstrip()

        # 5) Append the article URL to the last tweet
        if article_url:
            thread[-1] = thread[-1].rstrip() + f" Read more: {article_url}"

        # 6) Prepare image for first tweet
        img_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "content", "assets", "hunter_poses", "explaining.png"
        )
        media_id = upload_media(img_path) if os.path.exists(img_path) else None

        # 7) Post the 3-part thread on X
        result = post_thread(thread, category="explainer", media_id_first=media_id) or {}
        # Provide defaults if helper returned None or incomplete dict
        posted = result.get("posted", len(thread))
        total  = result.get("total", len(thread))
        error  = result.get("error")

        if posted == total:
            url = result.get("thread_url") or (result.get("tweets", [])[0].get("url") if result.get("tweets") else None)
            logger.info(f"✅ Posted explainer thread: {url} ({posted}/{total})")
        else:
            logger.warning(
                f"⚠️ Explainer thread incomplete: {posted}/{total} tweets posted"
                + (f" (error: {error})" if error else "")
            )

    except Exception as e:
        logger.error(f"❌ Failed to complete explainer pipeline: {e}")
        # Re-raise so the job fails properly when there are real issues
        raise