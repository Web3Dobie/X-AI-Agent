import schedule
import time
import logging
from content.market_summary import post_market_summary_thread
from content.news_recap import post_news_thread
from content.opinion_thread import post_top_news_thread
from content.explainer import post_dobie_explainer_thread
from content.random_post import post_random_content
from content.reply_handler import reply_to_comments
from content.ta_thread_generator import generate_ta_thread_with_memory
from utils.headline_pipeline import fetch_and_score_headlines
from utils.post_explainer_combo import post_explainer_combo
from utils.rotate_logs import rotate_logs
from utils.rotate_logs import clear_xrp_flag
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(filename='logs/activity.log', level=logging.INFO, format='%(asctime)s - %(message)s')

print("🕒 Hunter Scheduler is live. Waiting for scheduled posts...")

def post_top_news_if_not_friday():
    if datetime.now(timezone.utc).weekday() != 4:  # 0 = Monday, 4 = Friday
        post_top_news_thread()
    else:
        logging.info("📭 Skipped Hunter Reacts on Friday (Hunter Explains runs today).")

import random

def schedule_random_post_between(start_hour, end_hour):
    hour = random.randint(start_hour, end_hour - 1)
    minute = random.randint(0, 59)
    time_str = f"{hour:02d}:{minute:02d}"
    schedule.every().day.at(time_str).do(post_random_content)
    logging.info(f"🌀 Scheduled post_random_content at {time_str} (between {start_hour}:00–{end_hour}:00)")

def setup_daily_random_posts():
    clear_xrp_flag() #reset xrp flag
    schedule_random_post_between(16, 18)  # Morning window
    schedule_random_post_between(18, 20)  # Midday window
    schedule_random_post_between(20, 22)  # Afternoon window


def post_weekday_ta():
    weekday_token_map = {
        0: "btc",
        1: "eth",
        2: "sol",
        3: "xrp",
        4: "op"
    }
    weekday = datetime.now(timezone.utc).weekday()
    if weekday in weekday_token_map:
        token = weekday_token_map[weekday]
        try:
            thread = generate_ta_thread_with_memory(token)
            logging.info(f"🧠 Posted TA thread for ${token.upper()}")
        except Exception as e:
            logging.error(f"❌ Failed to post TA thread for ${token.upper()}: {e}")

def setup_weekend_random_posts():
    clear_xrp_flag()
    weekday = datetime.now(timezone.utc).weekday()
    if weekday in [5, 6]:  # Saturday or Sunday
        schedule_random_post_between(16, 18)
        schedule_random_post_between(18, 20)
        schedule_random_post_between(20, 22)
        logging.info("🎲 Weekend random posts scheduled.")
    else:
        logging.info("📅 Skipping random posts — it's a weekday.")


# --- Ingesting Headlines and Score them ---
schedule.every().hour.at(":05").do(fetch_and_score_headlines)

# --- Posting Schedule ---
# Weekday TA threads
schedule.every().monday.at("16:00").do(post_weekday_ta)
schedule.every().tuesday.at("16:00").do(post_weekday_ta)
schedule.every().wednesday.at("16:00").do(post_weekday_ta)
schedule.every().thursday.at("16:00").do(post_weekday_ta)
schedule.every().friday.at("16:00").do(post_weekday_ta)

schedule.every().day.at("13:00").do(post_news_thread)               # Morning headlines
schedule.every().day.at("14:00").do(post_market_summary_thread)     # Market update
schedule.every().day.at("00:01").do(setup_weekend_random_posts)       # Regenerate daily
schedule.every().day.at("18:00").do(lambda: reply_to_comments(bot_id=os.getenv("BOT_USER_ID")))
schedule.every().day.at("23:00").do(lambda: reply_to_comments(bot_id=os.getenv("BOT_USER_ID")))
schedule.every().day.at("23:45").do(post_top_news_if_not_friday)    # Evening opinion

# Weekly content
schedule.every().friday.at("23:00").do(post_explainer_combo)

# Rotate log files to D Drive
schedule.every().sunday.at("23:50").do(rotate_logs)

# Loop forever
while True:
    schedule.run_pending()
    time.sleep(30)