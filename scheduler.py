# scheduler.py - Complete working version with process-based HTTP server - FIXED
import sys
import os
import time
import signal
import tempfile
import traceback
import threading
import subprocess
import psutil
import requests
import socket
import logging
from datetime import datetime, timedelta
from functools import wraps
from enum import Enum
from typing import Optional, Dict, Any, Callable

import schedule
from dotenv import load_dotenv

# Import job registry system
from jobs.registry import JobRegistry, JobCategory, JobPriority
from jobs.definitions import setup_all_jobs, print_job_summary

# Import utilities
from process_http_manager import ProcessHTTPServer
from utils import rotate_logs
from utils.tg_notifier import send_telegram_message
from utils.telegram_log_handler import TelegramHandler

load_dotenv()

# REMOVED: Problematic stdout/stderr wrapping that caused I/O errors
# sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
# sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configure logging with enhanced file handling and directory creation
os.makedirs('/app/logs', exist_ok=True)  # Ensure logs directory exists
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/app/logs/scheduler.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Global rate limiting state
_last_telegram_send = 0
_telegram_send_interval = 1.0  # Minimum 1 second between messages

# Add Telegram handler ONLY to the root logger to avoid conflicts
def setup_telegram_logging():
    """Set up Telegram logging in a thread-safe way."""
    try:
        # Remove any existing TelegramHandler to avoid duplicates
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if isinstance(handler, TelegramHandler):
                root_logger.removeHandler(handler)
        
        # Add new TelegramHandler for ERROR level only (to reduce noise)
        tg_handler = TelegramHandler()
        tg_handler.setLevel(logging.ERROR)  # Only send errors to Telegram
        tg_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        
        # Add to root logger so all modules can use it
        root_logger.addHandler(tg_handler)
        logger.info("Telegram logging handler configured")
        
    except Exception as e:
        logger.warning(f"Failed to setup Telegram logging: {e}")

# Call setup function
setup_telegram_logging()

# Global monitoring stats
monitoring_stats = {
    "scheduler_start_time": time.time(),
    "jobs_executed": 0,
    "jobs_failed": 0,
    "last_job_time": None,
    "http_server_status": "starting",
    "server_ready": False
}

# Global job registry and HTTP server manager
job_registry = JobRegistry()
http_server_manager = None

def kill_process_on_port(port: int):
    """Find and kill any process that is listening on the specified port."""
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port and conn.status == 'LISTEN':
                try:
                    process = psutil.Process(conn.pid)
                    logger.warning(f"Found orphaned process {process.name()} (PID: {conn.pid}) on port {port}. Terminating it.")
                    process.terminate() # Send SIGTERM
                    process.wait(timeout=5) # Wait for it to die
                    logger.info(f"Process {conn.pid} terminated successfully.")
                except psutil.NoSuchProcess:
                    continue # Process already died
                except psutil.AccessDenied:
                    logger.error(f"Access denied to kill process {conn.pid}. Try running as root/sudo.")
                except Exception as e:
                    logger.error(f"Failed to kill process {conn.pid} on port {port}: {e}")
    except Exception as e:
        logger.error(f"Error while checking for processes on port {port}: {e}")

# ENHANCED: Notification function with proper logging and enhanced error handling
def send_telegram_log(message: str, level: str = "INFO", use_markdown: bool = False):
    """
    Send a log message to Telegram with enhanced error handling and rate limiting.
    """
    global _last_telegram_send
    
    prefix_map = {
        "INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", 
        "ERROR": "❌", "START": "🚀", "COMPLETE": "🏁", "HEARTBEAT": "❤️"
    }
    prefix = prefix_map.get(level.upper(), "🔹")
    
    timestamp = datetime.now().strftime('%H:%M:%S')

    try:
        # Rate limiting: ensure minimum interval between messages
        current_time = time.time()
        time_since_last = current_time - _last_telegram_send
        
        if time_since_last < _telegram_send_interval:
            sleep_time = _telegram_send_interval - time_since_last
            logger.debug(f"Telegram rate limiting: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
        
        # Handle markdown formatting safely
        if use_markdown:
            try:
                # Escape special characters for MarkdownV2
                safe_message = message.replace('.', '\\.').replace('-', '\\-').replace('!', '\\!')
                full_message = f"{prefix} *{level.upper()}* | `{timestamp}`\n{safe_message}"
                parse_mode = 'MarkdownV2'
            except Exception as markdown_error:
                logger.debug(f"Markdown formatting failed, falling back to plain text: {markdown_error}")
                full_message = f"{prefix} {level.upper()} | {timestamp}\n{message}"
                parse_mode = None
        else:
            full_message = f"{prefix} {level.upper()} | {timestamp}\n{message}"
            parse_mode = None
        
        # FIXED: Use proper logging instead of print()
        logger.debug(f"Sending Telegram message: {repr(full_message[:100])}...")
        
        send_telegram_message(full_message, parse_mode=parse_mode)
        _last_telegram_send = time.time()
        
        logger.debug(f"Sent Telegram: {level} - {message[:50]}...")

    except Exception as e:
        # FIXED: Use proper logging for errors instead of print()
        logger.error(f"Telegram notification failed: {e}")
        logger.debug(f"Failed message: {level} - {message}")
        
        # Enhanced fallback mechanism
        try:
            fallback_message = f"{prefix} {level.upper()} | {timestamp}\nTelegram fallback: {message}"
            send_telegram_message(fallback_message, parse_mode=None)
            logger.info("Telegram fallback succeeded")
        except Exception as final_e:
            logger.error(f"Complete Telegram failure: {final_e}")
        
        # Update timestamp even on failure to prevent spam retries
        _last_telegram_send = time.time()

def telegram_job_wrapper(job_name: str):
    """Decorator to log job execution and send Telegram notifications safely."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            monitoring_stats["last_job_time"] = start_time
            
            logger.info(f"Starting job: {job_name}")
            send_telegram_log(f"Starting job: {job_name}", "START", use_markdown=False)
            
            try:
                result = func(*args, **kwargs)
                monitoring_stats["jobs_executed"] += 1
                duration = datetime.now() - start_time
                
                logger.info(f"Completed job: {job_name} in {str(duration).split('.')[0]}")
                send_telegram_log(f"Completed job: {job_name}\nDuration: {str(duration).split('.')[0]}s", "COMPLETE", use_markdown=False)
                
                return result
                
            except Exception as e:
                monitoring_stats["jobs_failed"] += 1
                duration = datetime.now() - start_time
                
                error_details = traceback.format_exc()
                logger.error(f"Job failed: {job_name} - {str(e)}\n{error_details}")
                
                error_msg = (
                    f"Job Failure: {job_name}\n"
                    f"Duration: {str(duration).split('.')[0]}s\n"
                    f"Error: {str(e)}"
                )
                send_telegram_log(error_msg, "ERROR", use_markdown=False)

        return wrapper
    return decorator

# HTTP Server Management Functions
def start_http_server_with_verification():
    """Start HTTP server using process management with verification."""
    global http_server_manager
    
    logger.info("Starting process-managed HTTP server...")
    
    try:
        # Create server manager with notification callback
        http_server_manager = ProcessHTTPServer(
            port=3001,
            health_check_interval=30,
            notification_callback=send_telegram_log
        )
        
        # Start server process
        if http_server_manager.start_server_process():
            # Start monitoring
            http_server_manager.start_monitoring()
            
            # Update monitoring stats
            monitoring_stats["http_server_status"] = "healthy"
            monitoring_stats["server_ready"] = True
            
            logger.info("Process-managed HTTP server ready")
            return True
        else:
            logger.error("Failed to start process-managed HTTP server")
            monitoring_stats["http_server_status"] = "failed"
            return False
            
    except Exception as e:
        logger.error(f"HTTP server manager error: {e}")
        monitoring_stats["http_server_status"] = "crashed"
        send_telegram_log(f"HTTP server manager crashed: {e}", "ERROR")
        return False

def get_http_server_status():
    """Get detailed HTTP server status"""
    global http_server_manager
    
    if not http_server_manager:
        return {"status": "not_initialized", "details": None}
    
    try:
        status = http_server_manager.get_status()
        return {"status": "ok", "details": status}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def restart_http_server(reason: str = "Manual restart"):
    """Manually restart the HTTP server"""
    global http_server_manager
    
    if not http_server_manager:
        logger.error("HTTP server manager not initialized")
        return False
    
    try:
        return http_server_manager.restart_server(reason)
    except Exception as e:
        logger.error(f"Failed to restart server: {e}")
        return False

def stop_http_server():
    """Stop the HTTP server cleanly"""
    global http_server_manager
    
    if not http_server_manager:
        return True
    
    try:
        http_server_manager.stop_monitoring()
        return http_server_manager.stop_server()
    except Exception as e:
        logger.error(f"Error stopping HTTP server: {e}")
        return False

def graceful_shutdown():
    """Handle graceful shutdown of all services"""
    logger.info("Starting graceful shutdown...")
    
    # Stop HTTP server
    if stop_http_server():
        logger.info("HTTP server stopped cleanly")
    else:
        logger.warning("HTTP server stop had issues")
    
    logger.info("Graceful shutdown complete")

# System Health and Heartbeat
def get_system_health():
    """Get comprehensive system health details including process server status."""
    try:
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        uptime_seconds = time.time() - monitoring_stats["scheduler_start_time"]
        
        # Get HTTP server status from process manager
        http_status = get_http_server_status()
        http_healthy = http_status["status"] == "ok" and http_status["details"]["state"] == "running"
        
        return {
            "uptime_hours": round(uptime_seconds / 3600, 1),
            "jobs_executed": monitoring_stats["jobs_executed"],
            "jobs_failed": monitoring_stats["jobs_failed"],
            "http_responsive": http_healthy,
            "http_details": http_status,
            "memory_percent": f"{memory.percent:.1f}%",
            "cpu_percent": f"{cpu_percent:.1f}%",
        }
    except Exception as e:
        return {"error": str(e)}

@telegram_job_wrapper("system_heartbeat")
def send_system_heartbeat():
    """Sends a system health summary including HTTP server details to Telegram."""
    health = get_system_health()
    if "error" in health:
        send_telegram_log(f"Failed to get system health: {health['error']}", "WARNING")
        return

    # Get job registry stats
    total_jobs = len(job_registry.jobs)
    enabled_jobs = sum(1 for job in job_registry.jobs.values() if job['enabled'])
    
    # HTTP server details
    http_details = health.get('http_details', {})
    if http_details.get('status') == 'ok':
        server_info = http_details['details']
        server_emoji = "💚" if health['http_responsive'] else "💔"
        server_text = f"{server_emoji} HTTP: {server_info['state']} (PID: {server_info.get('process_id', 'N/A')})"
        
        # Add restart info if there have been restarts
        if server_info['stats']['total_restarts'] > 0:
            server_text += f" | Restarts: {server_info['stats']['total_restarts']}"
    else:
        server_text = "❌ HTTP: Error"
    
    message = (
        f"Uptime: {health['uptime_hours']}h\n"
        f"Memory: {health['memory_percent']} | CPU: {health['cpu_percent']}\n"
        f"Jobs OK: {health['jobs_executed']} | Jobs Failed: {health['jobs_failed']}\n"
        f"Registered Jobs: {enabled_jobs}/{total_jobs} enabled\n"
        f"{server_text}"
    )
    send_telegram_log(message, "HEARTBEAT", use_markdown=False)

# Job Scheduling
def run_in_thread(job_func):
    """Decorator to run a schedule job in a new thread."""
    @wraps(job_func)
    def wrapper(*args, **kwargs):
        job_thread = threading.Thread(target=job_func, args=args, kwargs=kwargs, daemon=True)
        job_thread.start()
    return wrapper

# Utility Functions
def get_job_status_report():
    """Get a detailed status report of all jobs"""
    report = []
    report.append("🔧 JOB REGISTRY STATUS REPORT")
    report.append("=" * 50)
    
    for category in JobCategory:
        stats = job_registry.get_category_stats(category)
        if not stats:
            continue
            
        report.append(f"\n📁 {category.value.upper().replace('_', ' ')}")
        report.append(f"   Jobs: {stats['total_jobs']}")
        report.append(f"   Executions: {stats['total_executions']}")
        report.append(f"   Failures: {stats['total_failures']}")
        report.append(f"   Success Rate: {stats['success_rate']:.1f}%")
        
        for job_name in stats['jobs']:
            job_stats = job_registry.get_job_stats(job_name)
            status = "✅" if job_registry.jobs[job_name]['enabled'] else "⏸️"
            
            if job_stats['last_run']:
                last_run = datetime.fromtimestamp(job_stats['last_run']).strftime('%H:%M:%S')
                report.append(f"   {status} {job_name}: Last run {last_run}")
            else:
                report.append(f"   {status} {job_name}: Never run")
    
    return "\n".join(report)

def emergency_disable_job(job_name: str):
    """Emergency function to disable a problematic job"""
    if job_name in job_registry.jobs:
        job_registry.disable_job(job_name)
        send_telegram_log(f"Emergency disabled job: {job_name}", "WARNING")
        logger.warning(f"Emergency disabled job: {job_name}")
    else:
        logger.error(f"Job not found for emergency disable: {job_name}")

def emergency_enable_job(job_name: str):
    """Emergency function to re-enable a job"""
    if job_name in job_registry.jobs:
        job_registry.enable_job(job_name)
        send_telegram_log(f"Re-enabled job: {job_name}", "SUCCESS")
        logger.info(f"Re-enabled job: {job_name}")
    else:
        logger.error(f"Job not found for emergency enable: {job_name}")

def signal_handler(signum, frame):
    """Handles SIGINT and SIGTERM for graceful shutdown."""
    logger.warning(f"Received signal {signum}. Initiating graceful shutdown...")
    graceful_shutdown()
    send_telegram_log(f"Scheduler stopped by signal {signum}.", "WARNING")
    sys.exit(0)

# Register the signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# ENHANCED: Directory safety checks for container environment
def ensure_container_directories():
    """Ensure all required directories exist in container environment"""
    directories = ['/app/logs', '/app/data', '/app/charts', '/app/backup', '/app/ta_posts', '/app/posts']
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {e}")

# Main Script Execution
if __name__ == "__main__":
    # Command line interface for job management
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "status":
            setup_all_jobs(job_registry)
            # FIXED: Use logging instead of print for status output
            status_report = get_job_status_report()
            logger.info(status_report)
            sys.exit(0)
            
        elif command == "list":
            setup_all_jobs(job_registry)
            print_job_summary(job_registry)
            sys.exit(0)
            
        elif command == "disable" and len(sys.argv) > 2:
            job_name = sys.argv[2]
            setup_all_jobs(job_registry)
            emergency_disable_job(job_name)
            sys.exit(0)
            
        elif command == "enable" and len(sys.argv) > 2:
            job_name = sys.argv[2]
            setup_all_jobs(job_registry)
            emergency_enable_job(job_name)
            sys.exit(0)
            
        elif command == "restart-server":
            logger.info("Manual server restart requested")
            restart_http_server("Manual CLI restart")
            sys.exit(0)
            
        else:
            # FIXED: Use logging instead of print for usage info
            usage_info = """Usage:
  python scheduler.py                  # Run scheduler
  python scheduler.py status           # Show job status
  python scheduler.py list             # List all jobs
  python scheduler.py disable <job>    # Disable job
  python scheduler.py enable <job>     # Enable job
  python scheduler.py restart-server   # Restart HTTP server"""
            logger.info(usage_info)
            sys.exit(1)

    # Main scheduler execution
    try:
        # ENHANCED: Ensure all directories exist
        ensure_container_directories()
        
        # Pre-emptively kill any process on our port before starting
        logger.info("Performing pre-startup cleanup...")
        kill_process_on_port(3001)
        
        # Startup sequence
        logger.info("Hunter Scheduler v2.0 starting up with Job Registry...")
        
        # Give systems a moment to initialize before first Telegram message
        time.sleep(2)
        
        # Setup job registry
        logger.info("Setting up job registry...")
        setup_all_jobs(job_registry)
        
        # Print job summary to console
        print_job_summary(job_registry)
        
        # Start and verify the HTTP server
        start_http_server_with_verification()

        # Schedule all jobs using registry
        logger.info("Scheduling jobs from registry...")
        scheduled_count = job_registry.schedule_all_jobs(schedule)
        
        # Add system heartbeat job manually (since it uses scheduler functions)
        job_registry.register_job(
            name="system_heartbeat",
            func=send_system_heartbeat,
            schedule_config={'type': 'interval', 'value': 15, 'unit': 'minutes'},
            category=JobCategory.MONITORING,
            priority=JobPriority.LOW,
            description="Send system health status to Telegram"
        )
        
        # Schedule the heartbeat job
        schedule.every(15).minutes.do(send_system_heartbeat)
        
        logger.info(f"Job registry setup complete. {scheduled_count + 1} jobs scheduled.")
        
        # Send startup notification with job summary
        category_summary = []
        for category in JobCategory:
            jobs = job_registry.get_category_jobs(category)
            if jobs:
                category_summary.append(f"{category.value}: {len(jobs)}")
        
        startup_message = (
            f"Scheduler v2.0 ready!\n"
            f"Jobs registered: {len(job_registry.jobs)}\n"
            f"Categories: {', '.join(category_summary)}\n"
            f"HTTP Server: {'Ready' if monitoring_stats['server_ready'] else 'Failed'}"
        )
        send_telegram_log(startup_message, "SUCCESS", use_markdown=False)
        
        # Main scheduler loop
        logger.info("Starting main scheduler loop...")
        loop_iterations = 0
        last_stats_report = time.time()
        
        while True:
            schedule.run_pending()
            loop_iterations += 1
            
            # Report stats every hour
            if time.time() - last_stats_report > 3600:  # 1 hour
                logger.info(f"Scheduler Stats: {loop_iterations} iterations, "
                          f"{monitoring_stats['jobs_executed']} jobs executed, "
                          f"{monitoring_stats['jobs_failed']} jobs failed")
                last_stats_report = time.time()
                loop_iterations = 0
            
            time.sleep(1)

    except KeyboardInterrupt:
        # This is now a fallback, the signal handler should catch Ctrl+C
        logger.info("KeyboardInterrupt caught. Shutting down.")
        
    except Exception as e:
        logger.critical(f"CRITICAL SCHEDULER CRASH: {e}", exc_info=True)
        crash_details = (
            f"The main scheduler process has crashed!\n"
            f"Error: {str(e)}\n\n"
            f"Check the logs immediately for the full traceback."
        )
        send_telegram_log(crash_details, "ERROR")
        
        # Try graceful shutdown even on crash
        try:
            graceful_shutdown()
        except Exception as shutdown_error:
            logger.error(f"Failed to shutdown cleanly: {shutdown_error}")