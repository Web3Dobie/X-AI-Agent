# scheduler.py - Fixed with proper HTTP server startup verification
import sys, io, logging
import os
import time
import traceback
import threading
import psutil
import requests
import socket
from datetime import datetime, timezone, timedelta
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
from utils.tg_notifier import send_telegram_message

load_dotenv()

BOT_ID = os.getenv("X_BOT_USER_ID")

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Global monitoring
monitoring_stats = {
    "scheduler_start_time": time.time(),
    "jobs_executed": 0,
    "jobs_failed": 0,
    "last_job_time": None,
    "http_server_status": "starting",
    "server_ready": False
}

def send_telegram_log(message: str, level: str = "INFO"):
    """Send formatted log message to Telegram with error handling"""
    emoji_map = {
        "INFO": "info",
        "SUCCESS": "check", 
        "WARNING": "warning",
        "ERROR": "x",
        "START": "rocket",
        "COMPLETE": "dart",
        "HEARTBEAT": "heart"
    }
    
    # Use simple text instead of emoji to avoid encoding issues
    prefix = emoji_map.get(level, "msg")
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    try:
        # Clean the message of problematic characters
        clean_message = str(message).encode('utf-8', 'ignore').decode('utf-8')
        
        # Build safe message
        safe_message = f"{prefix.upper()} {level} | {timestamp}\n{clean_message}"
        
        send_telegram_message(safe_message)
        
    except Exception as e:
        # Log locally but don't retry Telegram to avoid loops
        logging.error(f"Failed to send Telegram log: {e}")
        
        # Try one minimal fallback message
        try:
            fallback = f"{level} at {timestamp}"
            send_telegram_message(fallback)
        except:
            # Give up on Telegram, just log locally
            logging.warning(f"Telegram completely failed for: {level} - {message[:50]}")
            pass

def telegram_job_wrapper(job_name: str):
    """Enhanced decorator with safe logging only"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            monitoring_stats["last_job_time"] = start_time
            
            # Only log locally, no Telegram for start/complete
            logging.info(f"🚀 Starting job: {job_name}")
            
            try:
                result = func(*args, **kwargs)
                monitoring_stats["jobs_executed"] += 1
                duration = datetime.now() - start_time
                logging.info(f"✅ Completed job: {job_name} in {str(duration).split('.')[0]}")
                return result
                
            except Exception as e:
                monitoring_stats["jobs_failed"] += 1
                duration = datetime.now() - start_time
                
                # Only send critical errors to Telegram
                error_msg = f"CRITICAL JOB FAILURE: {job_name} - {str(e)}"
                try:
                    send_telegram_message(error_msg)
                except:
                    pass  # Don't fail on Telegram errors
                
                logging.error(f"❌ Job failed: {job_name} - {str(e)}")
                raise
                
        return wrapper
    return decorator

def test_server_connectivity(port=3001, timeout=5):
    """Test if server port is accepting connections"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
    except:
        return False

def test_http_server_health(timeout=10):
    """Test HTTP server health endpoint"""
    try:
        response = requests.get('http://localhost:3001/health', timeout=timeout)
        return response.status_code == 200, response.json() if response.status_code == 200 else {"error": f"HTTP {response.status_code}"}
    except requests.exceptions.Timeout:
        return False, {"error": "Health endpoint timeout"}
    except requests.exceptions.ConnectionError:
        return False, {"error": "Health endpoint connection refused"}
    except Exception as e:
        return False, {"error": str(e)}

def start_http_server_with_verification():
    """Start HTTP server with proper verification sequence"""
    
    def server_startup():
        """Server startup function for thread"""
        try:
            start_crypto_news_server(port=3001)
        except Exception as e:
            logger.error(f"❌ Server startup failed: {e}")
            monitoring_stats["http_server_status"] = "failed"
            send_telegram_log(f"HTTP server startup failed: {e}", "ERROR")
    
    try:
        logger.info("🌐 Starting crypto news HTTP server...")
        
        # Start server in background thread
        http_thread = threading.Thread(
            target=server_startup,
            daemon=True,
            name="CryptoHTTPServer"
        )
        http_thread.start()
        
        # Progressive verification with realistic timeouts
        verification_steps = [
            (3, "Port binding check"),
            (7, "Server initialization"),
            (15, "Full service verification")
        ]
        
        server_ready = False
        for wait_time, step_name in verification_steps:
            logger.info(f"⏳ {step_name} - waiting {wait_time}s...")
            time.sleep(wait_time)
            
            # Test port connectivity first
            if test_server_connectivity(3001, timeout=3):
                logger.info(f"✅ Port 3001 accepting connections after {wait_time}s")
                
                # Test health endpoint
                health_ok, health_data = test_http_server_health(timeout=10)
                if health_ok:
                    logger.info(f"✅ Health endpoint verified after {wait_time}s")
                    monitoring_stats["http_server_status"] = "healthy"
                    monitoring_stats["server_ready"] = True
                    server_ready = True
                    
                    send_telegram_log(
                        f"🚀 **HTTP Server Verified**\n"
                        f"📡 Port: 3001\n"
                        f"⏱️ Ready in: {wait_time}s\n"
                        f"💚 Health: OK\n"
                        f"🔗 Endpoint ready",
                        "SUCCESS"
                    )
                    break
                else:
                    logger.warning(f"⚠️ Port responsive but health endpoint failed: {health_data}")
            else:
                logger.debug(f"⏳ Port not ready yet after {wait_time}s...")
        
        if not server_ready:
            logger.error("❌ Server failed verification within 25 seconds")
            monitoring_stats["http_server_status"] = "failed_verification"
            send_telegram_log(
                "❌ **HTTP Server Failed Verification**\n"
                "Server may have started but not responding properly\n"
                "Check server logs for details",
                "ERROR"
            )
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Server startup process failed: {e}")
        monitoring_stats["http_server_status"] = "startup_error"
        send_telegram_log(f"💥 **Server Startup Error**\n{str(e)}", "ERROR")
        return False

def get_system_health():
    """Get comprehensive system health"""
    try:
        # System resources
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        disk = psutil.disk_usage('/')
        
        # HTTP server test
        http_healthy, http_status = test_http_server_health(timeout=5)
        
        # Scheduler stats
        uptime = time.time() - monitoring_stats["scheduler_start_time"]
        
        return {
            "timestamp": datetime.now().strftime('%H:%M:%S'),
            "uptime_hours": round(uptime / 3600, 1),
            "scheduler": {
                "jobs_executed": monitoring_stats["jobs_executed"],
                "jobs_failed": monitoring_stats["jobs_failed"], 
                "pending_jobs": len(schedule.get_jobs()),
                "success_rate": round((monitoring_stats["jobs_executed"] / max(1, monitoring_stats["jobs_executed"] + monitoring_stats["jobs_failed"])) * 100, 1)
            },
            "http_server": {
                "status": monitoring_stats["http_server_status"],
                "responsive": http_healthy,
                "details": http_status
            },
            "system": {
                "memory_used": f"{memory.percent:.1f}%",
                "cpu_usage": f"{cpu_percent:.1f}%",
                "disk_usage": f"{disk.percent:.1f}%"
            }
        }
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.now().strftime('%H:%M:%S')}

@telegram_job_wrapper("system_heartbeat")  
def send_system_heartbeat():
    """Send system heartbeat with minimal safe implementation"""
    try:
        health = get_system_health()
        
        # Extract basic info safely
        uptime = health.get('uptime_hours', 0)
        http_responsive = health.get("http_server", {}).get("responsive", False)
        
        # Create minimal message - just text, no special chars
        message = f"Heartbeat {datetime.now().strftime('%H:%M')} - Uptime {uptime:.1f}h - HTTP {'OK' if http_responsive else 'DOWN'}"
        
        # Direct Telegram API call instead of using the problematic wrapper
        import requests
        import os
        
        bot_token = os.getenv("TG_BOT_TOKEN")
        chat_id = os.getenv("TG_CHAT_ID")
        
        if bot_token and chat_id:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': None  # No markdown or HTML parsing
            }
            
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                logger.info("Heartbeat sent successfully")
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
        else:
            logger.warning("Missing Telegram credentials for heartbeat")
            
    except Exception as e:
        logger.error(f"Heartbeat completely failed: {e}")
        # Don't try to send error to Telegram to avoid loops

def run_in_thread(job_func):
    """Runs a function in a separate daemon thread."""
    thread = threading.Thread(target=job_func, daemon=True)
    thread.start()

# Example of how to apply this to your jobs
schedule.every().day.at("13:00").do(run_in_thread, telegram_job_wrapper("news_thread")(post_news_thread))
schedule.every().day.at("14:00").do(run_in_thread, telegram_job_wrapper("market_summary")(post_market_summary_thread))

def schedule_random_post_between(start_hour, end_hour):
    """Schedule random post between hours"""
    import random
    hour = random.randint(start_hour, end_hour - 1)
    minute = random.randint(0, 59)
    time_str = f"{hour:02d}:{minute:02d}"
    
    wrapped_func = telegram_job_wrapper(f"random_post_{time_str}")(post_random_content)
    schedule.every().day.at(time_str).do(wrapped_func)
    
    logging.info(f"🌀 Scheduled random post at {time_str}")

@telegram_job_wrapper("weekend_setup")
def setup_weekend_random_posts():
    """Setup weekend random posts"""
    clear_xrp_flag()
    weekday = datetime.now().weekday()
    if weekday in [5, 6]:
        schedule_random_post_between(16, 18)
        schedule_random_post_between(18, 20)
        schedule_random_post_between(20, 22)
        logging.info("🎲 Weekend random posts scheduled.")
    else:
        logging.info("📅 Skipping random posts — it's a weekday.")

def start_http_server_with_verification():
    """Start HTTP server with proper verification sequence"""
    
    def server_startup():
        """Server startup function for thread"""
        try:
            start_crypto_news_server(port=3001)
        except Exception as e:
            logger.error(f"❌ Server startup failed: {e}")
            monitoring_stats["http_server_status"] = "failed"
            send_telegram_log(f"HTTP server startup failed: {e}", "ERROR")
    
    try:
        logger.info("🌐 Starting crypto news HTTP server...")
        
        # Start server in background thread
        http_thread = threading.Thread(
            target=server_startup,
            daemon=True,
            name="CryptoHTTPServer"
        )
        http_thread.start()
        
        # Progressive verification with realistic timeouts
        verification_steps = [
            (3, "Port binding check"),
            (7, "Server initialization"), 
            (15, "Full service verification")
        ]
        
        server_ready = False
        for wait_time, step_name in verification_steps:
            logger.info(f"⏳ {step_name} - waiting {wait_time}s...")
            time.sleep(wait_time)
            
            # Test port connectivity first
            if test_server_connectivity(3001, timeout=3):
                logger.info(f"✅ Port 3001 accepting connections after {wait_time}s")
                
                # Test health endpoint
                health_ok, health_data = test_http_server_health(timeout=10)
                if health_ok:
                    logger.info(f"✅ Health endpoint verified after {wait_time}s")
                    monitoring_stats["http_server_status"] = "healthy"
                    monitoring_stats["server_ready"] = True
                    server_ready = True
                    
                    send_telegram_log(
                        f"🚀 **HTTP Server Verified**\n"
                        f"📡 Port: 3001\n"
                        f"⏱️ Ready in: {wait_time}s\n"
                        f"💚 Health: OK\n"
                        f"🔗 Endpoint ready",
                        "SUCCESS"
                    )
                    break
                else:
                    logger.warning(f"⚠️ Port responsive but health endpoint failed: {health_data}")
            else:
                logger.debug(f"⏳ Port not ready yet after {wait_time}s...")
        
        if not server_ready:
            logger.error("❌ Server failed verification within 25 seconds")
            monitoring_stats["http_server_status"] = "failed_verification"
            send_telegram_log(
                "❌ **HTTP Server Failed Verification**\n"
                "Server may have started but not responding properly\n"
                "Check server logs for details",
                "ERROR"
            )
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Server startup process failed: {e}")
        monitoring_stats["http_server_status"] = "startup_error"
        send_telegram_log(f"💥 **Server Startup Error**\n{str(e)}", "ERROR")
        return False

# === STARTUP SEQUENCE ===

print("🕒 Hunter Scheduler is live. Waiting for scheduled posts…")
sys.stdout.flush()

# Send startup notification
startup_message = (
    f"🎯 **Hunter Scheduler Started**\n"
    f"⏰ {datetime.now().strftime('%H:%M:%S')}\n"
    f"🤖 All scheduled jobs are now active\n"
    f"🌐 HTTP server starting on port 3001\n"
    f"💓 Heartbeat monitoring enabled"
)
send_telegram_log(startup_message, "SUCCESS")

# Start HTTP server with verification
print("🌐 Starting crypto news HTTP server with verification...")
server_started = start_http_server_with_verification()

if server_started:
    print("✅ HTTP server verified and ready")
    monitoring_stats["http_server_status"] = "verified_healthy"
else:
    print("❌ HTTP server failed verification - continuing with scheduler only")
    monitoring_stats["http_server_status"] = "failed"

# === SCHEDULED JOBS ===

# Headlines ingestion
schedule.every().hour.at(":05").do(
    telegram_job_wrapper("fetch_headlines")(fetch_and_score_headlines)
)

# Crypto news website generation
schedule.every().hour.at(":15").do(
    telegram_job_wrapper("crypto_news_website")(generate_crypto_news_for_website)
)

# Weekend posts
schedule.every().saturday.at("00:01").do(setup_weekend_random_posts)
schedule.every().sunday.at("00:01").do(setup_weekend_random_posts)

# Daily TA threads
def schedule_ta_thread(day, time_str):
    def ta_with_thread():
        run_in_thread(telegram_job_wrapper(f"ta_thread_{day.lower()}")(post_ta_thread))
    
    getattr(schedule.every(), day.lower()).at(time_str).do(ta_with_thread)

for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
    schedule_ta_thread(day, "16:00")

# Daily content with threading  
def schedule_threaded_job(time_str, func, job_name):
    def threaded_job():
        run_in_thread(telegram_job_wrapper(job_name)(func))
    
    schedule.every().day.at(time_str).do(threaded_job)

schedule_threaded_job("13:00", post_news_thread, "news_thread")
schedule_threaded_job("14:00", post_market_summary_thread, "market_summary")

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

@telegram_job_wrapper("system_heartbeat")  
def telegram_job_wrapper(job_name: str):
    """Decorator to log job execution and send Telegram notifications."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            monitoring_stats["last_job_time"] = start_time

            # Re-enabled start notification
            logging.info(f"🚀 Starting job: {job_name}")
            send_telegram_log(f"🚀 Starting job: {job_name}", "START")

            try:
                result = func(*args, **kwargs)
                monitoring_stats["jobs_executed"] += 1
                duration = datetime.now() - start_time
                
                # Re-enabled completion notification
                logging.info(f"✅ Completed job: {job_name} in {str(duration).split('.')[0]}")
                send_telegram_log(f"✅ Completed job: {job_name} in {str(duration).split('.')[0]}", "COMPLETE")

                return result
            except Exception as e:
                monitoring_stats["jobs_failed"] += 1
                duration = datetime.now() - start_time
                
                # Critical error notification
                error_msg = f"❌ CRITICAL JOB FAILURE: {job_name} in {str(duration).split('.')[0]} - {str(e)}"
                send_telegram_log(error_msg, "ERROR")
                
                logging.error(f"❌ Job failed: {job_name} - {str(e)}")
                # Optional: Depending on your needs, you might remove `raise` to prevent one failed job from stopping others.
                raise

        return wrapper
    return decorator

def send_telegram_log(message: str, level: str = "INFO"):
    """Send simple log message without markdown formatting"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    try:
        # Create plain text message - no markdown symbols
        clean_message = str(message).replace('**', '').replace('*', '').replace('`', '')
        plain_message = f"{level} {timestamp} {clean_message}"
        
        # This calls your utils/tg_notifier.py send_telegram_message function
        send_telegram_message(plain_message)
        
    except Exception as e:
        # Log locally but don't retry to avoid infinite loops
        logging.error(f"Telegram failed: {e}")

# Re-enable the heartbeat now that it's fixed
schedule.every(30).minutes.do(send_system_heartbeat)

# === MAIN SCHEDULER LOOP ===

try:
    logger.info("🔄 Starting main scheduler loop...")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            logger.error(f"❌ Scheduler loop error: {e}")
            send_telegram_log(f"Scheduler loop error: {str(e)}", "ERROR")
            time.sleep(60)  # Wait longer on errors
            
except KeyboardInterrupt:
    logger.info("🛑 Scheduler stopped by user")
    send_telegram_log("Hunter Scheduler Stopped 🛑\n💤 Manual shutdown", "WARNING")
    sys.exit(0)
    
except Exception as e:
    # Critical crash
    uptime = time.time() - monitoring_stats["scheduler_start_time"]
    
    crash_details = (
        f"💥 **CRITICAL SCHEDULER CRASH** 💥\n"
        f"⏰ {datetime.now().strftime('%H:%M:%S')}\n"
        f"⏳ Uptime: {uptime/3600:.1f} hours\n"
        f"✅ Jobs Executed: {monitoring_stats['jobs_executed']}\n"
        f"❌ Jobs Failed: {monitoring_stats['jobs_failed']}\n"
        f"🌐 HTTP Status: {monitoring_stats['http_server_status']}\n\n"
        f"🔥 **Error**: {str(e)}"
    )
    
    send_telegram_log(crash_details, "ERROR")
    logger.critical(f"CRITICAL CRASH: {str(e)}")
    logger.critical(traceback.format_exc())
    sys.exit(1)