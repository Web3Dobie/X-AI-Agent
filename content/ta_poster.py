"""
Weekly Technical Analysis Poster:
Runs on weekdays and posts a TA thread for the token mapped to that day.
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from threading import Lock

from content.ta_thread_generator import generate_ta_thread_with_memory
from utils import LOG_DIR, post_thread, get_module_logger
from utils.x_post import upload_media

logger = get_module_logger(__name__)

# Thread safety lock
_ta_thread_lock = Lock()
_last_ta_attempt = None

def post_ta_thread():
    """
    Determine today's token based on weekday and post its TA thread.
    Thread-safe implementation.
    """
    global _last_ta_attempt

    # Ensure only one thread can post at a time
    if not _ta_thread_lock.acquire(blocking=False):
        logger.warning("⚠️ Another TA thread is already running")
        return

    try:
        # Check if we've attempted recently (within 5 minutes)
        now = datetime.now(timezone.utc)
        if _last_ta_attempt and (now - _last_ta_attempt) < timedelta(minutes=5):
            logger.warning("⚠️ Skipping TA thread - too soon since last attempt")
            return

        _last_ta_attempt = now
        weekday_token_map = {0: "btc", 1: "eth", 2: "sol", 3: "xrp", 4: "doge"}
        weekday = now.weekday()

        if weekday in weekday_token_map:
            token = weekday_token_map[weekday]
            logger.info(f"🔍 Generating TA thread for {token.upper()} ({now.strftime('%Y-%m-%d')})")
            
            # ... rest of the existing logic ...

    except Exception as e:
        logger.error(f"❌ TA thread failed: {e}")

    finally:
        _ta_thread_lock.release()
        logger.info("🔒 TA thread lock released.")