
import logging
from datetime import datetime, timezone
from content.ta_thread_generator import generate_ta_thread_with_memory
from utils.x_post import post_thread

def post_ta_thread():
    weekday_token_map = {
        0: "btc",
        1: "eth",
        2: "sol",
        3: "xrp",
        4: "doge"
    }
    weekday = datetime.now(timezone.utc).weekday()
    if weekday in weekday_token_map:
        token = weekday_token_map[weekday]
        try:
            thread = generate_ta_thread_with_memory(token)
            post_thread(thread, category=f"ta_{token}")
            logging.info(f"✅ Posted TA thread for ${token.upper()}")
        except Exception as e:
            logging.error(f"❌ TA thread failed for ${token.upper()}: {e}")
