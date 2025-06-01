"""
Generates and posts a 3-part "Hunter Explains" thread on X for the top weekly headline.
"""

import logging
import os
from datetime import datetime

from utils import (LOG_DIR, generate_gpt_thread, get_top_headline_last_7_days,
                   post_thread)

# Configure logging
log_file = os.path.join(LOG_DIR, "explainer.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def post_dobie_explainer_thread(substack_url: str):
    """
    Fetch the top headline, generate a 3-part thread, and post on X.
    Appends the Substack article link at the end of the thread.
    """
    logging.info("🧵 Starting Dobie explainer thread generation")

    headline_entry = get_top_headline_last_7_days()
    if not headline_entry:
        logging.warning("❌ No headline found for explainer thread; aborting")
        return

    topic = headline_entry["headline"]
    source_url = headline_entry["url"]
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    prompt = f"""
Write a 3-part Twitter thread called 'Hunter Explains' about:
"{topic}"

Make it simple, clever, and accessible for casual readers. Add emojis and bold takes.
Each tweet must be <280 characters and end with '— Hunter 🐾'.
End the last tweet with a call to action and this link: {substack_url}
Start with: Hunter Explains 🧵 [{today_str}]
"""

    thread = generate_gpt_thread(prompt, max_parts=3)
    if not thread:
        logging.warning("⚠️ GPT returned no content for explainer thread; aborting")
        return

    # Prepend and append formatting
    thread[0] = f"Hunter Explains 🧵 [{today_str}]" + thread[0]
    thread[-1] += f" Read more: {substack_url}"

    try:
        post_thread(thread, category="explainer")
        logging.info("✅ Explainer thread posted successfully")
    except Exception as e:
        logging.error(f"❌ Failed to post explainer thread: {e}")
