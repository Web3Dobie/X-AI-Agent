
import logging
from datetime import datetime, timezone
from content.opinion_thread import post_top_news_thread

def post_top_news_or_skip():
    """Posts top news reaction unless it's Friday (reserved for explainer thread)."""
    if datetime.now(timezone.utc).weekday() != 4:  # Not Friday
        post_top_news_thread()
    else:
        logging.info("📭 Skipped Hunter Reacts on Friday (Hunter Explains runs today).")
