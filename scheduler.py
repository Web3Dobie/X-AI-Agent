# Enhanced scheduler.py with comprehensive monitoring
import sys, io, logging
import os
import time
import traceback
import threading
import psutil
import requests
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
from http_server import start_crypto_news_server

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
logger = logging.getLogger(__name__)

# Global monitoring state
monitoring_stats = {
    "scheduler_start_time": time.time(),
    "jobs_executed": 0,
    "jobs_failed": 0,
    "last_job_time": None,
    "http_server_status": "unknown"
}

def send_telegram_log(message: str, level: str = "INFO"):
    """Send formatted log message to Telegram"""
    emoji_map = {
        "INFO": "ℹ️",
        "SUCCESS": "✅", 
        "WARNING": "⚠️",
        "ERROR": "❌",
        "START": "🚀",
        "COMPLETE": "🎯",
        "HEARTBEAT": "💓"
    }
    
    emoji = emoji_map.get(level, "📝")
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    try:
        send_telegram_message(f"{emoji} **{level}** | {timestamp}\n{message}")
    except Exception as e:
        logging.error(f"Failed to send Telegram log: {e}")

def telegram_job_wrapper(job_name: str):
    """Enhanced decorator to wrap jobs with comprehensive monitoring"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            monitoring_stats["last_job_time"] = start_time
            
            # Log job start
            send_telegram_log(f"Starting: `{job_name}`", "START")
            logging.info(f"🚀 Starting job: {job_name}")
            
            try:
                # Execute the job
                result = func(*args, **kwargs)
                
                # Update success stats
                monitoring_stats["jobs_executed"] += 1
                
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
                # Update failure stats
                monitoring_stats["jobs_failed"] += 1
                
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

def test_http_server_connectivity():
    """Test if HTTP server is responding"""
    try:
        response = requests.get('http://localhost:3001/health', timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            monitoring_stats["http_server_status"] = "healthy"
            return True, health_data
        else:
            monitoring_stats["http_server_status"] = f"error_code_{response.status_code}"
            return False, {"error": f"HTTP {response.status_code}"}
    except requests.exceptions.Timeout:
        monitoring_stats["http_server_status"] = "timeout"
        return False, {"error": "Connection timeout"}
    except requests.exceptions.ConnectionError:
        monitoring_stats["http_server_status"] = "connection_refused"
        return False, {"error": "Connection refused"}
    except Exception as e:
        monitoring_stats["http_server_status"] = "unknown_error"
        return False, {"error": str(e)}

def get_system_health():
    """Get comprehensive system health status"""
    try:
        # System resources
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        disk = psutil.disk_usage('/')
        
        # Network tests
        http_healthy, http_status = test_http_server_connectivity()
        
        # Scheduler stats
        uptime = time.time() - monitoring_stats["scheduler_start_time"]
        pending_jobs = len(schedule.get_jobs())
        
        return {
            "timestamp": datetime.now().strftime('%H:%M:%S'),
            "uptime_hours": round(uptime / 3600, 1),
            "scheduler": {
                "jobs_executed": monitoring_stats["jobs_executed"],
                "jobs_failed": monitoring_stats["jobs_failed"],
                "pending_jobs": pending_jobs,
                "last_job": monitoring_stats["last_job_time"].strftime('%H:%M:%S') if monitoring_stats["last_job_time"] else "None",
                "success_rate": round((monitoring_stats["jobs_executed"] / max(1, monitoring_stats["jobs_executed"] + monitoring_stats["jobs_failed"])) * 100, 1)
            },
            "http_server": {
                "status": monitoring_stats["http_server_status"],
                "responsive": http_healthy,
                "details": http_status
            },
            "system": {
                "memory_used": f"{memory.percent:.1f}%",
                "memory_available": f"{memory.available / (1024**3):.1f}GB",
                "cpu_usage": f"{cpu_percent:.1f}%",
                "disk_usage": f"{disk.percent:.1f}%",
                "disk_free": f"{disk.free / (1024**3):.1f}GB"
            }
        }
    except Exception as e:
        return {
            "timestamp": datetime.now().strftime('%H:%M:%S'),
            "error": str(e),
            "status": "health_check_failed"
        }

@telegram_job_wrapper("system_heartbeat")
def send_comprehensive_heartbeat():
    """Send comprehensive system heartbeat to Telegram"""
    health = get_system_health()
    
    # Determine overall health status
    http_ok = health.get("http_server", {}).get("responsive", False)
    system_ok = (
        float(health.get("system", {}).get("memory_used", "100").rstrip('%')) < 90 and
        float(health.get("system", {}).get("cpu_usage", "100").rstrip('%')) < 80 and
        float(health.get("system", {}).get("disk_usage", "100").rstrip('%')) < 85
    )
    
    overall_status = "💚 HEALTHY" if (http_ok and system_ok) else "⚠️ ISSUES DETECTED"
    
    # Build comprehensive status message
    message = (
        f"💓 **System Heartbeat**\n"
        f"📊 **Overall**: {overall_status}\n"
        f"⏰ **Time**: {health['timestamp']}\n"
        f"🕐 **Uptime**: {health.get('uptime_hours', 0)}h\n\n"
        
        f"🤖 **Scheduler**:\n"
        f"• Jobs Executed: {health.get('scheduler', {}).get('jobs_executed', 0)}\n"
        f"• Jobs Failed: {health.get('scheduler', {}).get('jobs_failed', 0)}\n"
        f"• Success Rate: {health.get('scheduler', {}).get('success_rate', 0)}%\n"
        f"• Pending Jobs: {health.get('scheduler', {}).get('pending_jobs', 0)}\n"
        f"• Last Job: {health.get('scheduler', {}).get('last_job', 'None')}\n\n"
        
        f"🌐 **HTTP Server**:\n"
        f"• Status: {health.get('http_server', {}).get('status', 'unknown')}\n"
        f"• Responsive: {'✅' if http_ok else '❌'}\n"
    )
    
    # Add server details if available
    server_details = health.get('http_server', {}).get('details', {})
    if 'requests_served' in server_details:
        message += f"• Requests Served: {server_details['requests_served']}\n"
    if 'uptime_seconds' in server_details:
        message += f"• Server Uptime: {server_details['uptime_seconds'] / 3600:.1f}h\n"
    
    message += (
        f"\n💻 **System Resources**:\n"
        f"• Memory: {health.get('system', {}).get('memory_used', 'N/A')}\n"
        f"• CPU: {health.get('system', {}).get('cpu_usage', 'N/A')}\n"
        f"• Disk: {health.get('system', {}).get('disk_usage', 'N/A')}\n"
        f"• Free Space: {health.get('system', {}).get('disk_free', 'N/A')}"
    )
    
    # Add warnings for critical issues
    if not http_ok:
        message += "\n\n🚨 **HTTP SERVER NOT RESPONDING**"
    if not system_ok:
        message += "\n\n⚠️ **HIGH RESOURCE USAGE DETECTED**"
    
    send_telegram_message(message)

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

def start_http_server_in_background():
    """Start the HTTP server in a background thread"""
    try:
        start_crypto_news_server(port=3001)
    except Exception as e:
        send_telegram_log(f"HTTP server failed to start: {e}", "ERROR")

def run_in_thread(job_func):
    threading.Thread(target=job_func).start()

def schedule_random_post_between(start_hour, end_hour):
    import random
    hour = random.randint(start_hour, end_hour - 1)
    minute = random.randint(0, 59)
    time_str = f"{hour:02d}:{minute:02d}"
    
    wrapped_func = telegram_job_wrapper(f"random_post_{time_str}")(post_random_content)
    schedule.every().day.at(time_str).do(wrapped_func)
    
    logging.info(f"🌀 Scheduled post_random_content at {time_str} (between {start_hour}:00–{end_hour}:00)")

print("🕒 Hunter Scheduler is live. Waiting for scheduled posts…")
sys.stdout.flush()

# Send enhanced startup notification
startup_message = (
    f"🎯 **Hunter Scheduler Started**\n"
    f"⏰ {datetime.now().strftime('%H:%M:%S')}\n"
    f"🤖 All scheduled jobs are now active\n"
    f"🌐 HTTP server starting on port 3001\n"
    f"💓 Heartbeat monitoring enabled"
)
send_telegram_log(startup_message, "SUCCESS")

# Start HTTP server in background thread
print("🌐 Starting crypto news HTTP server...")
http_thread = threading.Thread(target=start_http_server_in_background, daemon=True)
http_thread.start()

# Add a small delay to let the server start
time.sleep(3)

# Test server connectivity and notify
http_healthy, http_status = test_http_server_connectivity()
if http_healthy:
    send_telegram_log("🚀 HTTP server confirmed running on port 3001", "SUCCESS")
else:
    send_telegram_log(f"⚠️ HTTP server connectivity issue: {http_status.get('error', 'unknown')}", "WARNING")

# --- SCHEDULED JOBS ---

# Ingesting Headlines and Score them
schedule.every().hour.at(":05").do(
    telegram_job_wrapper("fetch_headlines")(fetch_and_score_headlines)
)

# Crypto News Website Generation
schedule.every().hour.at(":15").do(
    telegram_job_wrapper("crypto_news_website")(generate_crypto_news_for_website)
)

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

# --- ENHANCED MONITORING SCHEDULE ---

# Comprehensive heartbeat every 30 minutes
schedule.every(30).minutes.do(send_comprehensive_heartbeat)

# Quick HTTP server check every 10 minutes
@telegram_job_wrapper("http_server_check")
def quick_server_check():
    """Quick HTTP server connectivity check"""
    http_healthy, http_status = test_http_server_connectivity()
    
    if not http_healthy:
        # Send alert for server issues
        alert_msg = (
            f"🚨 **HTTP Server Alert**\n"
            f"❌ Server not responding\n"
            f"📡 Error: {http_status.get('error', 'Unknown')}\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        )
        send_telegram_log(alert_msg, "ERROR")
    else:
        # Log successful check (debug level)
        logger.debug("💚 HTTP server health check passed")

schedule.every(10).minutes.do(quick_server_check)

# Resource monitoring every hour
@telegram_job_wrapper("resource_monitor")
def monitor_system_resources():
    """Monitor system resources and alert on high usage"""
    try:
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        disk = psutil.disk_usage('/')
        
        # Alert thresholds
        alerts = []
        if memory.percent > 85:
            alerts.append(f"🔴 High Memory: {memory.percent:.1f}%")
        if cpu_percent > 80:
            alerts.append(f"🔴 High CPU: {cpu_percent:.1f}%")
        if disk.percent > 90:
            alerts.append(f"🔴 Low Disk Space: {disk.percent:.1f}% used")
        
        if alerts:
            alert_message = "⚠️ **Resource Alert**\n" + "\n".join(alerts)
            send_telegram_message(alert_message)
            logger.warning(f"Resource alerts: {alerts}")
        else:
            logger.info(f"✅ System resources OK - Memory: {memory.percent:.1f}%, CPU: {cpu_percent:.1f}%, Disk: {disk.percent:.1f}%")
            
    except Exception as e:
        logger.error(f"❌ Resource monitoring failed: {e}")

schedule.every().hour.at(":30").do(monitor_system_resources)

# --- MAIN SCHEDULER LOOP ---

# Enhanced heartbeat tracking
last_heartbeat = time.time()
heartbeat_interval = 1800  # Send detailed heartbeat every 30 minutes
quick_heartbeat_interval = 600  # Quick status every 10 minutes
last_quick_heartbeat = time.time()

try:
    while True:
        schedule.run_pending()
        
        current_time = time.time()
        
        # Quick heartbeat every 10 minutes
        if current_time - last_quick_heartbeat > quick_heartbeat_interval:
            try:
                # Quick status update
                pending_jobs = len(schedule.get_jobs())
                jobs_executed = monitoring_stats["jobs_executed"]
                jobs_failed = monitoring_stats["jobs_failed"]
                
                quick_status = (
                    f"⚡ **Quick Status**\n"
                    f"⏰ {datetime.now().strftime('%H:%M')}\n"
                    f"📋 Pending: {pending_jobs} jobs\n"
                    f"✅ Executed: {jobs_executed}\n"
                    f"❌ Failed: {jobs_failed}"
                )
                
                # Only send if there are issues or significant activity
                if jobs_failed > 0 or monitoring_stats["http_server_status"] != "healthy":
                    send_telegram_log(quick_status, "HEARTBEAT")
                
                last_quick_heartbeat = current_time
                
            except Exception as e:
                logger.error(f"❌ Quick heartbeat failed: {e}")
        
        # Detailed heartbeat every 30 minutes
        if current_time - last_heartbeat > heartbeat_interval:
            try:
                health = get_system_health()
                
                # Build detailed heartbeat message
                uptime_hours = health.get('uptime_hours', 0)
                scheduler_stats = health.get('scheduler', {})
                http_status = health.get('http_server', {})
                system_stats = health.get('system', {})
                
                # Determine overall health
                http_ok = http_status.get('responsive', False)
                high_resources = (
                    float(system_stats.get('memory_used', '0').rstrip('%')) > 85 or
                    float(system_stats.get('cpu_usage', '0').rstrip('%')) > 80 or
                    float(system_stats.get('disk_usage', '0').rstrip('%')) > 90
                )
                
                if http_ok and not high_resources and scheduler_stats.get('jobs_failed', 0) == 0:
                    status_emoji = "💚"
                    status_text = "ALL SYSTEMS HEALTHY"
                elif http_ok and scheduler_stats.get('jobs_failed', 0) == 0:
                    status_emoji = "💛"
                    status_text = "MINOR ISSUES"
                else:
                    status_emoji = "💔"
                    status_text = "ISSUES DETECTED"
                
                detailed_heartbeat = (
                    f"{status_emoji} **{status_text}**\n"
                    f"⏰ {health['timestamp']} | ⏳ {uptime_hours}h uptime\n\n"
                    
                    f"🤖 **Scheduler Performance**:\n"
                    f"• Success Rate: {scheduler_stats.get('success_rate', 0)}%\n"
                    f"• Jobs Executed: {scheduler_stats.get('jobs_executed', 0)}\n"
                    f"• Jobs Failed: {scheduler_stats.get('jobs_failed', 0)}\n"
                    f"• Pending: {scheduler_stats.get('pending_jobs', 0)}\n"
                    f"• Last Job: {scheduler_stats.get('last_job', 'None')}\n\n"
                    
                    f"🌐 **HTTP Server**:\n"
                    f"• Status: {http_status.get('status', 'unknown')}\n"
                    f"• Responsive: {'✅' if http_ok else '❌'}\n"
                )
                
                # Add server details if available
                server_details = http_status.get('details', {})
                if 'requests_served' in server_details:
                    detailed_heartbeat += f"• Requests: {server_details['requests_served']}\n"
                if 'uptime_seconds' in server_details:
                    server_uptime = server_details['uptime_seconds'] / 3600
                    detailed_heartbeat += f"• Server Uptime: {server_uptime:.1f}h\n"
                
                detailed_heartbeat += (
                    f"\n💻 **System Resources**:\n"
                    f"• Memory: {system_stats.get('memory_used', 'N/A')} "
                    f"({system_stats.get('memory_available', 'N/A')} free)\n"
                    f"• CPU: {system_stats.get('cpu_usage', 'N/A')}\n"
                    f"• Disk: {system_stats.get('disk_usage', 'N/A')} "
                    f"({system_stats.get('disk_free', 'N/A')} free)"
                )
                
                # Add critical alerts
                if not http_ok:
                    detailed_heartbeat += "\n\n🚨 **CRITICAL**: HTTP server not responding!"
                if high_resources:
                    detailed_heartbeat += "\n\n⚠️ **WARNING**: High resource usage detected!"
                
                send_telegram_message(detailed_heartbeat)
                last_heartbeat = current_time
                
            except Exception as e:
                logger.error(f"❌ Detailed heartbeat failed: {e}")
                # Send minimal heartbeat as fallback
                fallback_msg = (
                    f"💓 **Fallback Heartbeat**\n"
                    f"⏰ {datetime.now().strftime('%H:%M')}\n"
                    f"⚠️ Monitoring error: {str(e)}"
                )
                send_telegram_log(fallback_msg, "WARNING")
                last_heartbeat = current_time
        
        time.sleep(30)
        
except KeyboardInterrupt:
    logging.info("Scheduler stopped by user (SIGINT)")
    send_telegram_log("Hunter Scheduler Stopped 🛑\n👤 Manual shutdown via SIGINT", "WARNING")
    sys.exit(0)
    
except Exception as e:
    # Critical crash with enhanced error reporting
    uptime = time.time() - monitoring_stats["scheduler_start_time"]
    uptime_hours = uptime / 3600
    
    error_details = (
        f"💥 **CRITICAL SCHEDULER CRASH** 💥\n"
        f"⏰ {datetime.now().strftime('%H:%M:%S')}\n"
        f"⏳ Uptime: {uptime_hours:.1f} hours\n"
        f"✅ Jobs Executed: {monitoring_stats['jobs_executed']}\n"
        f"❌ Jobs Failed: {monitoring_stats['jobs_failed']}\n\n"
        f"🔥 **Error Details**:\n"
        f"```\n{str(e)}\n{traceback.format_exc()}\n```"
    )
    
    send_telegram_log(error_details, "ERROR")
    logging.critical(f"CRITICAL SCHEDULER CRASH: {str(e)}")
    logging.critical(traceback.format_exc())
    sys.exit(1)