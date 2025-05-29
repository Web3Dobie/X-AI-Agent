import logging
import os
from datetime import datetime

from content.explainer import post_dobie_explainer_thread
from content.explainer_writer import generate_substack_explainer

from .config import LOG_DIR
from .substack_client import SubstackClient

# Set up a dedicated logger for this workflow
log_file = os.path.join(LOG_DIR, "post_explainer_combo.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

client = SubstackClient()


def post_explainer_combo():
    """
    Friday Explainer Combo:
      1) Generate a Substack article via generate_substack_explainer()
      2) Publish it (draft → publish) and retrieve the URL
      3) Post a 3-part thread on X linking to the article
    """
    logging.info("🚀 Starting post_explainer_combo")

    # 1) Generate the Substack article
    logging.info("📝 Generating Substack explainer article")
    article = generate_substack_explainer()
    if not article:
        logging.error("❌ Article generation failed; aborting combo.")
        return

    title = article["headline"]
    body_md = article["content"]
    # Schedule for immediate publish
    publish_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    # 2) Publish via Substack API
    try:
        logging.info("📚 Publishing to Substack")
        post = client.publish(title, body_md, publish_at)
        # Extract canonical URL
        post_data = post.get("post", {}) or post
        substack_url = (
            post_data.get("canonical_url")
            or f"https://{client.slug}.substack.com/p/{post_data.get('slug')}"
        )
        logging.info(f"✅ Published Substack article at {substack_url}")
    except Exception as e:
        logging.error(f"❌ Substack publish failed: {e}")
        return

    # 3) Post the X thread
    try:
        logging.info("📢 Posting explainer thread on X")
        post_dobie_explainer_thread(substack_url=substack_url)
        logging.info("✅ Explainer thread posted")
    except Exception as e:
        logging.error(f"❌ Failed to post explainer thread: {e}")


if __name__ == "__main__":
    post_explainer_combo()
