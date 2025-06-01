import logging
import os
from datetime import datetime

from content.ta_substack_generator import generate_weekly_ta_article

from .config import LOG_DIR
from .substack_client import SubstackClient
from .x_post import post_thread

# Setup logging for this combo
log_file = os.path.join(LOG_DIR, "post_ta_weekly_combo.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

client = SubstackClient()


def post_ta_weekly_combo():
    """
    Weekly Technical Analysis Combo:
      1) Generate weekly TA Substack article.
      2) Publish it via the Substack API (draft → publish).
      3) Post a tweet on X linking to the article.
    """
    logging.info("[ROCKET] Starting post_ta_weekly_combo")

    # 1) Generate the Substack article markdown
    logging.info("[WRITE] Generating weekly TA Substack article")
    filepath = generate_weekly_ta_article()
    if not filepath or not os.path.exists(filepath):
        logging.error("[ERROR] TA article generation failed; aborting combo.")
        return

    # Extract title and body from markdown
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    if not lines:
        logging.error("[ERROR] Generated markdown is empty; aborting.")
        return
    # Title is the first heading line
    title = lines[0].lstrip("# ").strip()
    body_md = "".join(lines[1:])

    # 2) Publish via Substack API
    publish_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    try:
        logging.info("[WRITE] Publishing TA article to Substack")
        post = client.publish(title, body_md, publish_at)
        post_data = post.get("post", {}) or post
        substack_url = (
            post_data.get("canonical_url")
            or f"https://{client.slug}.substack.com/p/{post_data.get('slug')}"
        )
        logging.info(f"[OK] Published TA article at {substack_url}")
    except Exception as e:
        logging.error(f"[ERROR] Failed to publish TA article: {e}")
        return

    # 3) Post update on X
    try:
        message = (
            f"📈 Our Weekly Technical Analysis is live! Read it here: {substack_url}"
        )
        logging.info("[ALERT] Posting weekly TA update on X")
        post_thread([message], category="ta_weekly")
        logging.info("[OK] Weekly TA update posted on X")
    except Exception as e:
        logging.error(f"[ERROR] Failed to post TA update on X: {e}")


if __name__ == "__main__":
    post_ta_weekly_combo()
