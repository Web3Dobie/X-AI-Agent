# scheduler.py - Corrected and Improved
import sys, io, logging
import os
import time
import traceback
import threading
import psutil
import requests
import socket
from datetime import datetime
from functools import wraps

import schedule
from dotenv import load_dotenv

# Import your modules
from content.market_summary import post_market_summary_thread
from content.news_recap import post_news_thread
from content.random_post import post_random_content
from content.reply_handler import reply_to_comments
from content.ta_poster import post_ta_thread
from content.top_news_or_explainer import post_top_news_or_skip
from content.explainer_writer import generate_substack_explainer
from content.ta_substack_generator import generate_ta_substack_article
from crypto_news_bridge import generate_crypto_news_for_website
from http_server import start_crypto_news_server

from utils import (
    clear_xrp_flag, 
    fetch_and_score_headlines, 
    rotate_logs
)
# CORRECTED: Import the updated function
from utils.tg_notifier import send_telegram_message

load_dotenv()

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Global monitoring stats
monitoring_stats = {
    "scheduler_start_time": time.time(),
    "jobs_executed": 0,
    "jobs_failed": 0,
    "last_job_time": None,
    "http_server_status": "starting",
    "server_ready": False
}

# --- IMPROVED NOTIFICATION AND JOB WRAPPER ---

def send_telegram_log(message: str, level: str = "INFO", use_markdown: bool = False):
    """
    IMPROVED: Send a log message to Telegram, using Markdown only when safe.
    """
    # Simple prefixes for clarity
    prefix_map = {
        "INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", 
        "ERROR": "❌", "START": "🚀", "COMPLETE": "🏁", "HEARTBEAT": "❤️"
    }
    prefix = prefix_map.get(level.upper(), "🔹")
    
    # Always include a timestamp
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    # Construct the final message
    full_message = f"{prefix} *{level.upper()}* | `{timestamp}`\n{message}"

    try:
        # Determine parse_mode. Errors and unsafe content should be plain text.
        parse_mode = 'MarkdownV2' if use_markdown else None
        
        # For MarkdownV2, we must escape certain characters in the user message part
        if parse_mode == 'MarkdownV2':
            # This is a basic escaper, you might need to expand it
            safe_message = message.replace('.', '\\.').replace('-', '\\-').replace('!', '\\!')
            full_message = f"{prefix} *{level.upper()}* | `{timestamp}`\n{safe_message}"
        else:
             full_message = f"{prefix} {level.upper()} | {timestamp}\n{message}"

        send_telegram_message(full_message, parse_mode=parse_mode)

    except Exception as e:
        # If sending fails, log it locally and try sending a minimal plain text alert.
        logging.error(f"Primary Telegram notification failed: {e}")
        try:
            fallback_message = f"❌ ERROR | {timestamp}\nTelegram notifier failed. Check logs."
            send_telegram_message(fallback_message, parse_mode=None)
        except Exception as final_e:
            logging.critical(f"FATAL: Telegram fallback failed. Logging is down. {final_e}")


def telegram_job_wrapper(job_name: str):
    """
    IMPROVED: Decorator to log job execution and send Telegram notifications safely.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            monitoring_stats["last_job_time"] = start_time
            
            logging.info(f"🚀 Starting job: {job_name}")
            send_telegram_log(f"Starting job: `{job_name}`", "START", use_markdown=True)
            
            try:
                result = func(*args, **kwargs)
                monitoring_stats["jobs_executed"] += 1
                duration = datetime.now() - start_time
                
                logging.info(f"✅ Completed job: {job_name} in {str(duration).split('.')[0]}")
                send_telegram_log(f"Completed job: `{job_name}`\nDuration: {str(duration).split('.')[0]}s", "COMPLETE", use_markdown=True)
                
                return result
                
            except Exception as e:
                monitoring_stats["jobs_failed"] += 1
                duration = datetime.now() - start_time
                
                error_details = traceback.format_exc()
                logging.error(f"❌ Job failed: {job_name} - {str(e)}\n{error_details}")
                
                # KEY FIX: Send error messages as PLAIN TEXT to avoid parsing errors.
                error_msg = (
                    f"Job Failure: {job_name}\n"
                    f"Duration: {str(duration).split('.')[0]}s\n"
                    f"Error: {str(e)}"
                )
                send_telegram_log(error_msg, "ERROR", use_markdown=False)
                # Do not re-raise, to allow other jobs to run.
                # If you want the whole scheduler to stop on one error, add `raise` here.

        return wrapper
    return decorator

# --- HTTP SERVER AND HEALTH CHECKS ---

def test_server_connectivity(port=3001, timeout=5):
    """Test if server port is accepting connections."""
    try:
        with socket.create_connection(("localhost", port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError):
        return False
    except Exception:
        return False

def test_http_server_health(timeout=10):
    """Test HTTP server health endpoint."""
    try:
        response = requests.get('http://localhost:3001/health', timeout=timeout)
        if response.status_code == 200:
            return True, response.json()
        return False, {"error": f"HTTP Status {response.status_code}"}
    except requests.RequestException as e:
        return False, {"error": f"Connection failed: {e}"}

def start_http_server_with_verification():
    """Start HTTP server in a thread and verify it's ready."""
    
    def server_thread_target():
        try:
            start_crypto_news_server(port=3001)
        except Exception as e:
            logger.error(f"❌ HTTP Server thread crashed: {e}")
            monitoring_stats["http_server_status"] = "crashed"
            send_telegram_log(f"HTTP server crashed: {e}", "ERROR")

    logger.info("🌐 Starting crypto news HTTP server...")
    http_thread = threading.Thread(target=server_thread_target, daemon=True, name="CryptoHTTPServer")
    http_thread.start()
    
    # Wait and check for the server to become healthy
    for attempt in range(5):
        time.sleep(5) # Wait 5s between checks
        logger.info(f"Verifying server... (Attempt {attempt + 1}/5)")
        is_healthy, health_data = test_http_server_health()
        if is_healthy:
            logger.info("✅ Health endpoint verified. Server is ready.")
            monitoring_stats["http_server_status"] = "healthy"
            monitoring_stats["server_ready"] = True
            send_telegram_log("HTTP Server is verified and healthy.", "SUCCESS")
            return True
            
    logger.error("❌ Server verification failed after 25 seconds.")
    monitoring_stats["http_server_status"] = "unhealthy"
    send_telegram_log("HTTP Server failed verification. It may be running but is not responding to health checks.", "ERROR")
    return False

# --- SYSTEM HEALTH & HEARTBEAT ---

def get_system_health():
    """Get comprehensive system health details."""
    try:
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        uptime_seconds = time.time() - monitoring_stats["scheduler_start_time"]
        http_healthy, http_details = test_http_server_health()
        
        return {
            "uptime_hours": round(uptime_seconds / 3600, 1),
            "jobs_executed": monitoring_stats["jobs_executed"],
            "jobs_failed": monitoring_stats["jobs_failed"],
            "http_responsive": http_healthy,
            "memory_percent": f"{memory.percent:.1f}%",
            "cpu_percent": f"{cpu_percent:.1f}%",
        }
    except Exception as e:
        return {"error": str(e)}

# SIMPLIFIED: Re-enable the heartbeat using the corrected notifier
@telegram_job_wrapper("system_heartbeat")
def send_system_heartbeat():
    """Sends a system health summary to Telegram."""
    health = get_system_health()
    if "error" in health:
        send_telegram_log(f"Failed to get system health: {health['error']}", "WARNING")
        return

    message = (
        f"Uptime: *{health['uptime_hours']}h*\n"
        f"Memory: `{health['memory_percent']}` | CPU: `{health['cpu_percent']}`\n"
        f"Jobs OK: *{health['jobs_executed']}* | Jobs Failed: *{health['jobs_failed']}*\n"
        f"HTTP Server: {'*OK*' if health['http_responsive'] else '*DOWN*'}"
    )
    send_telegram_log(message, "HEARTBEAT", use_markdown=True)


# --- JOB SCHEDULING ---

def run_in_thread(job_func):
    """Decorator to run a schedule job in a new thread."""
    @wraps(job_func)
    def wrapper(*args, **kwargs):
        job_thread = threading.Thread(target=job_func, args=args, kwargs=kwargs, daemon=True)
        job_thread.start()
    return wrapper

# === MAIN SCRIPT EXECUTION ===

if __name__ == "__main__":
    try:
        # --- STARTUP SEQUENCE ---
        send_telegram_log(
            "Hunter Scheduler is starting up...", "SUCCESS", use_markdown=True
        )
        
        # Start and verify the HTTP server
        start_http_server_with_verification()

        # --- SCHEDULED JOBS ---
        logging.info("Setting up scheduled jobs...")

        # Core daily/hourly jobs
        schedule.every().hour.at(":05").do(run_in_thread, telegram_job_wrapper("fetch_headlines")(fetch_and_score_headlines))
        schedule.every().hour.at(":15").do(run_in_thread, telegram_job_wrapper("generate_crypto_news")(generate_crypto_news_for_website))
        schedule.every().day.at("13:00").do(run_in_thread, telegram_job_wrapper("post_news_thread")(post_news_thread))
        schedule.every().day.at("14:00").do(run_in_thread, telegram_job_wrapper("post_market_summary")(post_market_summary_thread))
        schedule.every().day.at("16:00").do(run_in_thread, telegram_job_wrapper("post_ta_thread")(post_ta_thread))
        schedule.every().day.at("23:45").do(run_in_thread, telegram_job_wrapper("post_top_news")(post_top_news_or_skip))
        
        # Weekly/Maintenance jobs
        schedule.every().friday.at("23:45").do(run_in_thread, telegram_job_wrapper("generate_substack_explainer")(generate_substack_explainer))
        schedule.every().sunday.at("18:00").do(run_in_thread, telegram_job_wrapper("generate_ta_substack")(generate_ta_substack_article))
        schedule.every().sunday.at("23:50").do(run_in_thread, telegram_job_wrapper("rotate_logs")(rotate_logs))

        # System Heartbeat
        schedule.every(15).minutes.do(send_system_heartbeat)

        logger.info("✅ All jobs scheduled. Starting main loop...")
        
        # --- MAIN SCHEDULER LOOP ---
        while True:
            schedule.run_pending()
            time.sleep(1) # Sleep for a short duration

    except KeyboardInterrupt:
        logger.info("🛑 Scheduler stopped by user.")
        send_telegram_log("Scheduler stopped manually.", "WARNING")
    
    except Exception as e:
        logger.critical(f"💥 CRITICAL SCHEDULER CRASH: {e}", exc_info=True)
        crash_details = (
            f"The main scheduler process has crashed!\n"
            f"Error: {str(e)}\n\n"
            f"Check the logs immediately for the full traceback."
        )
        send_telegram_log(crash_details, "ERROR")