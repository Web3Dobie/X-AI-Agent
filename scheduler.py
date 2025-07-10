import sys, io, logging
import os
import time
from datetime import datetime, timezone, timedelta

import schedule
from dotenv import load_dotenv

# from utils.post_explainer_combo import post_explainer_combo
from content.market_summary import post_market_summary_thread
from content.news_recap import post_news_thread
from content.random_post import post_random_content
from content.reply_handler import reply_to_comments
from content.ta_poster import post_ta_thread
from content.top_news_or_explainer import post_top_news_or_skip
from content.explainer_writer import generate_substack_explainer
from content.ta_substack_generator import generate_ta_substack_article
from utils import (clear_xrp_flag, fetch_and_score_headlines, rotate_logs)
from world3_agent.listing_alerts import run_listing_alerts
from world3_agent.bnb_token_sniffer import run_bnb_token_sniffer




load_dotenv()

BOT_ID = os.getenv("X_BOT_USER_ID")

# Re-wrap stdout/stderr so they use UTF-8 instead of cp1252:
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')



logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    stream=sys.stdout  # you can explicitly point it at the rewrapped stdout
)

print("🕒 Hunter Scheduler is live. Waiting for scheduled posts…")
sys.stdout.flush()

import threading

def run_in_thread(job_func):
    threading.Thread(target=job_func).start()



# function now moved to top_news_or_explainer.py
#    if datetime.now(timezone.utc).weekday() != 4:  # 0 = Monday, 4 = Friday
#        post_top_news_thread()
#    else:
#        logging.info("📭 Skipped Hunter Reacts on Friday (Hunter Explains runs today).")

import random


def schedule_random_post_between(start_hour, end_hour):
    hour = random.randint(start_hour, end_hour - 1)
    minute = random.randint(0, 59)
    time_str = f"{hour:02d}:{minute:02d}"
    schedule.every().day.at(time_str).do(post_random_content)
    logging.info(
        f"🌀 Scheduled post_random_content at {time_str} (between {start_hour}:00–{end_hour}:00)"
    )


def setup_weekend_random_posts():
    clear_xrp_flag()
    weekday = datetime.now().weekday()  # local timezone
    if weekday in [5, 6]:
        schedule_random_post_between(16, 18)
        schedule_random_post_between(18, 20)
        schedule_random_post_between(20, 22)
        logging.info("🎲 Weekend random posts scheduled.")
    else:
        logging.info("📅 Skipping random posts — it's a weekday.")


# --- Ingesting Headlines and Score them ---
schedule.every().hour.at(":05").do(fetch_and_score_headlines)

# --- Posting Schedule ---
# schedule.every(20).minutes.do(lambda: run_in_thread(run_listing_alerts))
# schedule.every().hour.at(":37").do(lambda: run_in_thread(run_bnb_token_sniffer))
schedule.every().saturday.at("00:01").do(setup_weekend_random_posts)
schedule.every().sunday.at("00:01").do(setup_weekend_random_posts)
schedule.every().monday.at("16:00").do(lambda: run_in_thread(post_ta_thread))
schedule.every().tuesday.at("16:00").do(lambda: run_in_thread(post_ta_thread))
schedule.every().wednesday.at("16:00").do(lambda: run_in_thread(post_ta_thread))
schedule.every().thursday.at("16:00").do(lambda: run_in_thread(post_ta_thread))
schedule.every().friday.at("16:00").do(lambda: run_in_thread(post_ta_thread))

schedule.every().day.at("13:00").do(lambda: run_in_thread(post_news_thread))
schedule.every().day.at("14:00").do(lambda: run_in_thread(post_market_summary_thread))
# schedule.every().day.at("18:00").do(lambda: run_in_thread(lambda: reply_to_comments(bot_id=BOT_ID)))
# schedule.every().day.at("23:00").do(lambda: run_in_thread(lambda: reply_to_comments(bot_id=BOT_ID)))
schedule.every().day.at("23:45").do(post_top_news_or_skip)
schedule.every().friday.at("23:45").do(generate_substack_explainer)
schedule.every().sunday.at("18:00").do(generate_ta_substack_article)
schedule.every().sunday.at("23:50").do(rotate_logs)

while True:
    schedule.run_pending()
    time.sleep(30)
