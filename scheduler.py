import schedule
import time
import logging
from content.market_summary import post_market_summary_thread
from content.news_recap import post_news_thread
from content.opinion_thread import post_top_news_thread
from content.explainer import post_dobie_explainer_thread
from content.random_post import post_random_content
from content.reply_handler import reply_to_comments
from utils.headline_pipeline import fetch_and_score_headlines
from utils.post_explainer_combo import post_explainer_combo
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(filename='logs/activity.log', level=logging.INFO, format='%(asctime)s - %(message)s')

print("🕒 Hunter Scheduler is live. Waiting for scheduled posts...")

# --- Ingesting Headlines and Score them ---
schedule.every().hour.at(":05").do(fetch_and_score_headlines)

# --- Posting Schedule ---
schedule.every().day.at("08:00").do(post_news_thread)               # Morning headlines
schedule.every().day.at("09:00").do(post_market_summary_thread)     # Market update
schedule.every().day.at("10:00").do(post_random_content)            # Random engagement
schedule.every().day.at("13:00").do(lambda: reply_to_comments(bot_id=os.getenv("BOT_USER_ID")))
schedule.every().day.at("18:00").do(lambda: reply_to_comments(bot_id=os.getenv("BOT_USER_ID")))
schedule.every().day.at("20:00").do(post_top_news_thread)           # Evening opinion

# Weekly content
schedule.every().friday.at("16:00").do(post_explainer_combo)

# Loop forever
while True:
    schedule.run_pending()
    time.sleep(30)