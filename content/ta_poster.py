"""
Weekly Technical Analysis Poster:
Runs on weekdays and posts a TA thread for the token mapped to that day.
"""

import logging
import os
from datetime import datetime, timezone

from content.ta_thread_generator import generate_ta_thread_with_memory
from utils import LOG_DIR, post_thread

# Configure logging
log_file = os.path.join(LOG_DIR, "ta_poster.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def post_ta_thread():
    """
    Determine today's token based on weekday and post its TA thread.
    Monday=0 → BTC, Tuesday=1 → ETH, ..., Friday=4 → DOGE.
    """
    weekday_token_map = {0: "btc", 1: "eth", 2: "sol", 3: "xrp", 4: "doge"}
    today = datetime.now(timezone.utc)
    weekday = today.weekday()

    if weekday in weekday_token_map:
        token = weekday_token_map[weekday]
        logging.info(
            f"🔍 Generating TA thread for {token.upper()} ({today.strftime('%Y-%m-%d')})"
        )
        try:
            thread_parts = generate_ta_thread_with_memory(token)
            if not thread_parts:
                logging.warning(f"⚠️ No TA thread generated for {token.upper()}")
                return
            post_thread(thread_parts, category=f"ta_{token}")
            logging.info(f"✅ Posted TA thread for {token.upper()}")
        except Exception as e:
            logging.error(f"❌ TA thread failed for {token.upper()}: {e}")
    else:
        logging.info(f"⏭ No TA thread today (weekday {weekday})")


if __name__ == "__main__":
    post_ta_thread()
