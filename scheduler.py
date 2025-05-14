import schedule
import time
import logging
import os
from datetime import datetime
from content_engine import post_random_content
from news_poster import post_news_thread
from news_threader import post_top_news_thread
from market_threader import post_market_summary_thread
from log_follower_count import log_follower_count
from metrics_logger import fetch_tweet_metrics
from generate_weekly_report import generate_weekly_report
from generate_top3_report import generate_top3_report
from headline_manager import ingest_and_score_headlines
from tweet_limit_guard import has_reached_daily_limit
from post_utils import post_reply_to_kol, post_thread, reply_to_comments

safe_mode = True

logging.basicConfig(filename='logs/activity.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Ingest headlines every hour
schedule.every().hour.at(":05").do(ingest_and_score_headlines)

# Metrics (disabled in safe mode)
if not safe_mode:
    schedule.every().day.at("06:00").do(fetch_tweet_metrics)
    schedule.every().day.at("06:05").do(log_follower_count)

# Engagement reporting
schedule.every().day.at("07:00").do(lambda: logging.info("📊 Engagement score for " + str(datetime.utcnow().date()) + ": 1"))

# Daily threads
schedule.every().day.at("08:00").do(post_news_thread)
schedule.every().day.at("09:00").do(post_market_summary_thread)
schedule.every().day.at("10:00").do(post_random_content)
schedule.every().day.at("14:00").do(post_reply_to_kol)
schedule.every().day.at("18:00").do(lambda: reply_to_comments(bot_id=os.getenv("BOT_USER_ID")))
schedule.every().day.at("20:00").do(post_top_news_thread)

# Weekly reports
schedule.every().sunday.at("23:00").do(generate_weekly_report)
schedule.every().sunday.at("23:05").do(generate_top3_report)

print("🕒 Smart scheduler is live. Waiting for scheduled posts...")

while True:
    schedule.run_pending()
    time.sleep(1)