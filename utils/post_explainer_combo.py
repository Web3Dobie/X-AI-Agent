# post_explainer_combo.py

import logging
import os
from datetime import datetime

from content.explainer import post_dobie_explainer_thread
from content.explainer_writer import generate_substack_explainer

from utils.config import LOG_DIR
from utils.substack_client import SubstackClient

# ────────────────────────────────────────────────────────────────────────────────
# SET UP DEDICATED LOGGING (clear root handlers so nothing goes to rss_fetch.log)
logger = logging.getLogger("post_explainer_combo")
logger.setLevel(logging.INFO)

log_file = os.path.join(LOG_DIR, "post_explainer_combo.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)

handler = logging.FileHandler(log_file, encoding="utf-8")
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

root = logging.getLogger()
for h in root.handlers[:]:
    root.removeHandler(h)
root.addHandler(handler)
root.setLevel(logging.INFO)

logger.addHandler(handler)
logger.propagate = False
# ────────────────────────────────────────────────────────────────────────────────

client = SubstackClient()

def post_explainer_combo():
    """
    Friday Explainer Combo:
      1) Generate a Substack article via generate_substack_explainer()
      2) Strip out the “**Title:**” line from the generated content
      3) Prepend "# <headline>" so SubstackClient.publish() picks up the title
      4) Replace any plain @Web3_Dobie with a Markdown link
      5) Publish it (draft → publish) and retrieve the URL
      6) Post a 3-part thread on X linking to the article
    """
    logger.info("[ROCKET] Starting post_explainer_combo")

    # 1) Generate the Substack article
    logger.info("[WRITE] Generating Substack explainer article")
    article = generate_substack_explainer()
    if not article:
        logger.error("[ERROR] Article generation failed; aborting combo.")
        return

    # 2) Pull out the headline and raw body
    headline = article.get("headline", "").strip()
    raw_body = article.get("content", "").strip()
    if not headline or not raw_body:
        logger.error("[ERROR] Missing headline or content in generated article.")
        return

    # 3) Remove any "**Title:** ..." line from raw_body
    clean_lines = []
    for line in raw_body.splitlines():
        if line.strip().startswith("**Title:"):
            continue
        clean_lines.append(line)
    clean_body_md = "\n".join(clean_lines).strip()

    # 4) Turn any plain @Web3_Dobie into a Markdown link
    #    so it renders as: [@Web3_Dobie](https://twitter.com/Web3_Dobie)
    clean_body_md = clean_body_md.replace(
        "@Web3_Dobie", "[@Web3_Dobie](https://twitter.com/Web3_Dobie)"
    )

    # 5) Prepend "# <headline>" so publish() can extract the title cleanly
    full_md = f"# {headline}\n\n{clean_body_md}"

    # 6) Decide on publish timestamp (immediate, in UTC)
    publish_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    # 7) Publish via Substack API
    try:
        logger.info("[WRITE] Publishing to Substack")
        post = client.publish(body_md=full_md, published_at=publish_at)

        post_data = post.get("post", {}) or post
        substack_url = (
            post_data.get("canonical_url")
            or f"https://{client.slug}.substack.com/p/{post_data.get('slug')}"
        )
        logger.info(f"[OK] Published Substack article at {substack_url}")
    except Exception as e:
        logger.error(f"[ERROR] Substack publish failed: {e}")
        return

    # 8) Post the 3-part thread on X
    try:
        logger.info("[INFO] Posting explainer thread on X")
        post_dobie_explainer_thread(substack_url=substack_url)
        logger.info("[OK] Explainer thread posted")
    except Exception as e:
        logger.error(f"[ERROR] Failed to post explainer thread: {e}")

if __name__ == "__main__":
    post_explainer_combo()
