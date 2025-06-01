# explainer.py

"""
Generates and posts a 3-part "Hunter Explains" thread on X for the top weekly headline.
"""

import logging
from datetime import datetime
import os

from utils import (
    LOG_DIR,
    generate_gpt_thread,
    get_top_headline_last_7_days,
    post_thread,
)

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
    Appends the Substack article link exactly once at the end of the final tweet.
    """
    logging.info("🧵 Starting Dobie explainer thread generation")

    # 1) Grab last week's top headline
    headline_entry = get_top_headline_last_7_days()
    if not headline_entry:
        logging.warning("❌ No headline found for explainer thread; aborting")
        return

    topic = headline_entry["headline"]
    source_url = headline_entry["url"]
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    # 2) Build a prompt that asks for a 3-part thread BUT does not insert the header/ link itself
    prompt = f"""
Write a 3-part Twitter thread called 'Hunter Explains' about:
\"{topic}\"

Make it simple, clever, and accessible for casual readers. Add emojis and bold takes.
Each tweet must be <280 characters and end with '— Hunter 🐾'.
(Do NOT include the header "Hunter Explains 🧵 [date]" or the Substack link in the tweets themselves—those will be added manually.)
"""

    thread = generate_gpt_thread(prompt, max_parts=3)
    if not thread:
        logging.warning("⚠️ GPT returned no content for explainer thread; aborting")
        return

    # 3) Prepend exactly one "Hunter Explains 🧵 [YYYY-MM-DD]" header + blank line to the first tweet
    header = f"Hunter Explains 🧵 [{today_str}]\n\n"
    thread[0] = header + thread[0].lstrip()  # lstrip() to avoid accidental leading whitespace

    # 4) Append "Read more: {substack_url}" exactly once on the last tweet
    #    (remove any trailing whitespace before adding)
    thread[-1] = thread[-1].rstrip() + f" Read more: {substack_url}"

    # 5) Post the 3-part thread on X
    try:
        post_thread(thread, category="explainer")
        logging.info("✅ Explainer thread posted successfully")
    except Exception as e:
        logging.error(f"❌ Failed to post explainer thread: {e}")
