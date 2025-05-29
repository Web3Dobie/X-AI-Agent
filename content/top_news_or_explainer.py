"""
Decision logic to post either the daily opinion thread or skip on Fridays
to allow the Substack explainer flow to run instead.
"""

import logging
import os
from datetime import datetime, timezone

from content.explainer import post_dobie_explainer_thread
from content.opinion_thread import post_top_news_thread
from utils import LOG_DIR

# Configure logging
log_file = os.path.join(LOG_DIR, "top_news_or_explainer.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def post_top_news_or_skip(substack_url: str = None):
    """
    If today is Friday (weekday=4), run the Substack explainer thread
    using the provided substack_url. Otherwise, post the top news opinion thread.
    """
    today = datetime.now(timezone.utc)
    if today.weekday() == 4:
        logging.info(
            "📭 Friday detected — running explainer thread instead of top news reaction."
        )
        if substack_url:
            post_dobie_explainer_thread(substack_url=substack_url)
        else:
            logging.warning("⚠️ No substack_url provided for explainer thread.")
    else:
        logging.info("🔄 Posting top news reaction thread.")
        post_top_news_thread()
