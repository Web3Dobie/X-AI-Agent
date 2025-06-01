"""
Generic orchestration: generate → publish → announce workflow helper.
Logs operations to a dedicated log file in the LOG_DIR.
"""

import logging
import os

from .config import LOG_DIR

# Configure logging for publisher
log_file = os.path.join(LOG_DIR, "publisher.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def publish_and_announce(generate_fn, publish_fn, announce_fn, announce_args_builder):
    """
    Orchestrate:
      1) generate_fn -> returns either:
         - filepath (for markdown-based publish)
         - (title, body_markdown) tuple (for dynamic publish)
      2) publish_fn(...) -> returns the public URL of the published post
      3) announce_fn(*args, **kwargs) -> posts on X or sends notifications
    announce_args_builder(url) should return (args_list, kwargs_dict) for announce_fn.
    """
    logging.info("[ROCKET] Starting publish_and_announce workflow")
    try:
        data = generate_fn()
        logging.info("[OK] Content generated successfully")
    except Exception as e:
        logging.error(f"[ERROR] generate_fn failed: {e}")
        return

    try:
        if isinstance(data, tuple):
            url = publish_fn(*data)
        else:
            url = publish_fn(data)
        logging.info(f"[OK] Published content, received URL: {url}")
    except Exception as e:
        logging.error(f"[ERROR] publish_fn failed: {e}")
        return

    try:
        args, kwargs = announce_args_builder(url)
        announce_fn(*args, **kwargs)
        logging.info("[OK] Announcement sent successfully")
    except Exception as e:
        logging.error(f"[ERROR] announce_fn failed: {e}")
