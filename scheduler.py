import sys, io, logging
import os
import time
import traceback
from datetime import datetime, timezone, timedelta
from functools import wraps

import schedule
from dotenv import load_dotenv

# Fixed imports - removed obsolete modules
from content.market_summary import post_market_summary_thread
from content.news_recap import post_news_thread
from content.random_post import post_random_content
from content.reply_handler import reply_to_comments
from content.ta_poster import post_ta_thread
from content.top_news_or_explainer import post_top_news_or_skip
from content.explainer_writer import generate_substack_explainer
from content.ta_substack_generator import generate_ta_substack_article
from crypto_news_bridge import generate_crypto_news_for_website

# Import utilities - only what exists
from utils import (
    clear_xrp_flag, 
    fetch_and_score_headlines, 
    rotate_logs
)

# Import Telegram notifier
from utils.tg_notifier import send_telegram_message

load_dotenv()

BOT_ID = os.getenv("X_BOT_USER_ID")

# Re-wrap stdout/stderr so they use UTF-8 instead of cp1252:
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    stream=sys.stdout
)

def send_telegram_log(message: str, level: str = "INFO"):
    """Send formatted log message to Telegram"""
    emoji_map = {
        "INFO": "ℹ️",
        "SUCCESS": "✅", 
        "WARNING": "⚠️",
        "ERROR": "❌",
        "START": "🚀",
        "COMPLETE": "🎯"
    }
    
    emoji = emoji_map.get(level, "📝")
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    try:
        send_telegram_message(f"{emoji} **{level}** | {timestamp}\n{message}")
    except Exception as e:
        logging.error(f"Failed to send Telegram log: {e}")

def telegram_job_wrapper(job_name: str):
    """Decorator to wrap jobs with Telegram logging"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            # Log job start
            send_telegram_log(f"Starting: `{job_name}`", "START")
            logging.info(f"🚀 Starting job: {job_name}")
            
            try:
                # Execute the job
                result = func(*args, **kwargs)
                
                # Calculate duration
                duration = datetime.now() - start_time
                duration_str = str(duration).split('.')[0]  # Remove microseconds
                
                # Log successful completion
                send_telegram_log(
                    f"Completed: `{job_name}`\n⏱️ Duration: {duration_str}", 
                    "COMPLETE"
                )
                logging.info(f"✅ Completed job: {job_name} in {duration_str}")
                
                return result
                
            except Exception as e:
                # Calculate duration even for failed jobs
                duration = datetime.now() - start_time
                duration_str = str(duration).split('.')[0]
                
                # Log error with details
                error_msg = f"Failed: `{job_name}`\n⏱️ Duration: {duration_str}\n❌ Error: {str(e)}"
                send_telegram_log(error_msg, "ERROR")
                
                # Also log full traceback locally
                logging.error(f"❌ Job failed: {job_name}")
                logging.error(f"Error: {str(e)}")
                logging.error(traceback.format_exc())
                
                # Re-raise to maintain original behavior
                raise
                
        return wrapper
    return decorator

print("🕒 Hunter Scheduler is live. Waiting for scheduled posts…")
sys.stdout.flush()

# Send startup notification
send_telegram_log("Hunter Scheduler Started 🎯\nAll scheduled jobs are now active", "SUCCESS")

import threading

def run_in_thread(job_func):
    threading.Thread(target=job_func).start()

import random

def schedule_random_post_between(start_hour, end_hour):
    hour = random.randint(start_hour, end_hour - 1)
    minute = random.randint(0, 59)
    time_str = f"{hour:02d}:{minute:02d}"
    
    wrapped_func = telegram_job_wrapper(f"random_post_{time_str}")(post_random_content)
    schedule.every().day.at(time_str).do(wrapped_func)
    
    logging.info(f"🌀 Scheduled post_random_content at {time_str} (between {start_hour}:00–{end_hour}:00)")

@telegram_job_wrapper("weekend_setup")
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
schedule.every().hour.at(":05").do(
    telegram_job_wrapper("fetch_headlines")(fetch_and_score_headlines)
)

# --- Crypto News Website Generation ---
schedule.every().hour.at(":15").do(
    telegram_job_wrapper("crypto_news_website")(generate_crypto_news_for_website)
)
# --- Posting Schedule ---

# WEEKEND RANDOM POSTS COMMENTED OUT - WILL ADD OTHER WEEKEND CONTENT LATER
# Weekend setup
# schedule.every().saturday.at("00:01").do(setup_weekend_random_posts)
# schedule.every().sunday.at("00:01").do(setup_weekend_random_posts)

# Daily TA threads with threading wrapper
def schedule_ta_thread(day, time_str):
    def ta_with_thread():
        run_in_thread(telegram_job_wrapper(f"ta_thread_{day.lower()}")(post_ta_thread))
    
    getattr(schedule.every(), day.lower()).at(time_str).do(ta_with_thread)

# Schedule TA threads for weekdays
for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
    schedule_ta_thread(day, "16:00")

# Daily content with threading
def schedule_threaded_job(time_str, func, job_name):
    def threaded_job():
        run_in_thread(telegram_job_wrapper(job_name)(func))
    
    schedule.every().day.at(time_str).do(threaded_job)

schedule_threaded_job("13:00", post_news_thread, "news_thread")
schedule_threaded_job("14:00", post_market_summary_thread, "market_summary")

# Reply handling (commented out but with wrapper ready)
# def schedule_reply_handler(time_str, job_name):
#     def reply_job():
#         run_in_thread(telegram_job_wrapper(job_name)(lambda: reply_to_comments(bot_id=BOT_ID)))
#     
#     schedule.every().day.at(time_str).do(reply_job)

# schedule_reply_handler("18:00", "reply_handler_evening")
# schedule_reply_handler("23:00", "reply_handler_night")

# Evening content
schedule.every().day.at("23:45").do(
    telegram_job_wrapper("top_news_or_skip")(post_top_news_or_skip)
)

# Weekly content
schedule.every().friday.at("23:45").do(
    telegram_job_wrapper("substack_explainer")(generate_substack_explainer)
)
schedule.every().sunday.at("18:00").do(
    telegram_job_wrapper("ta_substack_article")(generate_ta_substack_article)
)

# Maintenance
schedule.every().sunday.at("23:50").do(
    telegram_job_wrapper("log_rotation")(rotate_logs)
)

# Add heartbeat monitoring
last_heartbeat = time.time()
heartbeat_interval = 3600  # Send heartbeat every hour

try:
    while True:
        schedule.run_pending()
        
        # Send periodic heartbeat
        current_time = time.time()
        if current_time - last_heartbeat > heartbeat_interval:
            pending_jobs = len(schedule.get_jobs())
            send_telegram_log(
                f"Scheduler Heartbeat 💓\n⏰ {datetime.now().strftime('%H:%M')} - {pending_jobs} jobs scheduled",
                "INFO"
            )
            last_heartbeat = current_time
            
        time.sleep(30)
        
except KeyboardInterrupt:
    logging.info("Scheduler stopped by user (SIGINT)")
    send_telegram_log("Hunter Scheduler Stopped 🛑\n👤 Manual shutdown via SIGINT", "WARNING")
    sys.exit(0)
    
except Exception as e:
    # Critical crash
    error_details = f"CRITICAL SCHEDULER CRASH: {str(e)}\n{traceback.format_exc()}"
    send_telegram_log(f"💥 CRITICAL CRASH 💥\n```\n{error_details}\n```", "ERROR")
    logging.critical(error_details)
    sys.exit(1)