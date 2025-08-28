# scheduler.py - Complete working version with process-based HTTP server
import sys
import io
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
from utils import rotate_logs
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

# Global job registry and HTTP server manager
job_registry = JobRegistry()
http_server_manager = None

# Process-based HTTP Server Management Classes
class ServerState(Enum):
    STOPPED = "stopped"
    STARTING = "starting" 
    RUNNING = "running"
    UNHEALTHY = "unhealthy"
    RESTARTING = "restarting"
    FAILED = "failed"

class RestartPolicy:
    """Restart policy with exponential backoff and circuit breaker"""
    
    def __init__(self, 
                 max_restarts_per_hour: int = 5,
                 base_backoff_seconds: int = 30,
                 max_backoff_seconds: int = 300,
                 circuit_breaker_threshold: int = 3):
        self.max_restarts_per_hour = max_restarts_per_hour
        self.base_backoff = base_backoff_seconds
        self.max_backoff = max_backoff_seconds
        self.circuit_breaker_threshold = circuit_breaker_threshold
        
        self.restart_history = []
        self.consecutive_failures = 0
        self.circuit_open = False
        self.circuit_open_until = None
        
    def can_restart(self) -> bool:
        """Check if restart is allowed based on policy"""
        now = datetime.now()
        
        # Check circuit breaker
        if self.circuit_open:
            if now < self.circuit_open_until:
                logger.warning(f"Circuit breaker open until {self.circuit_open_until}")
                return False
            else:
                logger.info("Circuit breaker reset")
                self.circuit_open = False
                self.consecutive_failures = 0
        
        # Clean old restart history (older than 1 hour)
        one_hour_ago = now - timedelta(hours=1)
        self.restart_history = [r for r in self.restart_history if r > one_hour_ago]
        
        # Check restart limit
        if len(self.restart_history) >= self.max_restarts_per_hour:
            logger.error(f"Restart limit reached: {len(self.restart_history)}/{self.max_restarts_per_hour} per hour")
            return False
            
        return True
    
    def get_backoff_delay(self) -> int:
        """Calculate backoff delay based on consecutive failures"""
        if self.consecutive_failures == 0:
            return 0
            
        delay = min(
            self.base_backoff * (2 ** (self.consecutive_failures - 1)),
            self.max_backoff
        )
        return delay
    
    def record_restart(self, success: bool = True):
        """Record restart attempt and update policy state"""
        now = datetime.now()
        self.restart_history.append(now)
        
        if success:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            
            if self.consecutive_failures >= self.circuit_breaker_threshold:
                self.circuit_open = True
                self.circuit_open_until = now + timedelta(minutes=15)
                logger.error(f"Circuit breaker OPENED after {self.consecutive_failures} failures")

class ProcessHTTPServer:
    """Process-based HTTP server with health monitoring and graceful restart"""
    
    def __init__(self, port: int = 3001, health_check_interval: int = 30, notification_callback: Optional[Callable] = None):
        self.port = port
        self.health_check_interval = health_check_interval
        self.notification_callback = notification_callback
        self.process: Optional[subprocess.Popen] = None
        self.state = ServerState.STOPPED
        self.restart_policy = RestartPolicy()
        
        # Monitoring
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitoring_active = False
        self.last_health_check = None
        self.start_time = None
        
        # Stats
        self.stats = {
            'total_starts': 0,
            'total_restarts': 0,
            'total_failures': 0,
            'uptime_seconds': 0,
            'last_restart_reason': None
        }
        
    def _send_notification(self, message: str, level: str = "INFO"):
        """Send notification via callback if available"""
        if self.notification_callback:
            try:
                self.notification_callback(message, level)
            except Exception as e:
                logger.warning(f"Notification callback failed: {e}")
        else:
            logger.info(f"Notification: {level} - {message}")
    
    def start_server_process(self) -> bool:
        """Start HTTP server as separate process"""
        if self.process and self.process.poll() is None:
            logger.warning("Server process already running")
            return True
            
        logger.info(f"Starting HTTP server process on port {self.port}")
        self.state = ServerState.STARTING
        
        try:
            # Create server startup script in temp directory
            script_content = f'''#!/usr/bin/env python3
import sys
import os

# Add the project root to Python path
project_root = "{os.path.dirname(os.path.abspath(__file__))}"
sys.path.insert(0, project_root)

try:
    # Import and start the server
    from http_server import start_crypto_news_server
    start_crypto_news_server(port={self.port})
except KeyboardInterrupt:
    print("Server stopped by signal")
except Exception as e:
    print(f"Server error: {{e}}")
    sys.exit(1)
'''
            
            # Create temporary script file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script_content)
                script_path = f.name
            
            # Start process
            self.process = subprocess.Popen([
                sys.executable, script_path
            ], 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            env=os.environ.copy(),
            preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            logger.info(f"Server process started with PID: {self.process.pid}")
            self.start_time = time.time()
            self.stats['total_starts'] += 1
            
            # Wait for server to become healthy
            if self._wait_for_healthy(timeout=30):
                self.state = ServerState.RUNNING
                self._send_notification(f"HTTP Server started successfully on port {self.port}", "SUCCESS")
                
                # Clean up temp script
                try:
                    os.unlink(script_path)
                except OSError:
                    pass
                
                return True
            else:
                logger.error("Server failed to become healthy")
                self.state = ServerState.FAILED
                self._cleanup_process()
                return False
                
        except Exception as e:
            logger.error(f"Failed to start server process: {e}")
            self.state = ServerState.FAILED
            self._send_notification(f"HTTP Server failed to start: {str(e)}", "ERROR")
            return False
    
    def _wait_for_healthy(self, timeout: int = 30) -> bool:
        """Wait for server to become healthy"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self._check_health():
                return True
            time.sleep(1)
            
        return False
    
    def _check_health(self) -> bool:
        """Check if server is healthy"""
        try:
            # Check if process is still running
            if not self.process or self.process.poll() is not None:
                return False
            
            # Check port connectivity
            if not self._test_port_connectivity():
                return False
                
            # Check HTTP health endpoint
            response = requests.get(
                f'http://localhost:{self.port}/health',
                timeout=5
            )
            
            if response.status_code == 200:
                self.last_health_check = time.time()
                return True
                
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            
        return False
    
    def _test_port_connectivity(self) -> bool:
        """Test if port is accepting connections"""
        try:
            with socket.create_connection(("localhost", self.port), timeout=3):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False
    
    def stop_server(self, timeout: int = 10) -> bool:
        """Stop server process gracefully"""
        if not self.process:
            logger.info("No server process to stop")
            return True
            
        logger.info(f"Stopping server process (PID: {self.process.pid})")
        self.state = ServerState.STOPPED
        
        try:
            # Try graceful shutdown first
            if os.name != 'nt':
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            else:
                self.process.terminate()
                
            # Wait for graceful shutdown
            try:
                self.process.wait(timeout=timeout)
                logger.info("Server stopped gracefully")
                return True
            except subprocess.TimeoutExpired:
                logger.warning("Graceful shutdown timeout, forcing kill")
                if os.name != 'nt':
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                else:
                    self.process.kill()
                self.process.wait()
                return True
                
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            return False
        finally:
            self._cleanup_process()
    
    def _cleanup_process(self):
        """Clean up process resources"""
        if self.process:
            self.process = None
        
        if self.start_time:
            self.stats['uptime_seconds'] += time.time() - self.start_time
            self.start_time = None
    
    def restart_server(self, reason: str = "Manual restart") -> bool:
        """Restart server with backoff policy"""
        logger.info(f"Restart requested: {reason}")
        self.stats['last_restart_reason'] = reason
        
        if not self.restart_policy.can_restart():
            logger.error("Restart denied by policy")
            self.stats['total_failures'] += 1
            return False
        
        # Calculate backoff delay
        delay = self.restart_policy.get_backoff_delay()
        if delay > 0:
            logger.info(f"Waiting {delay}s before restart (backoff policy)")
            self._send_notification(f"Server restart delayed {delay}s due to recent failures", "WARNING")
            time.sleep(delay)
        
        self.state = ServerState.RESTARTING
        
        # Stop current process
        stop_success = self.stop_server()
        
        # Start new process
        start_success = self.start_server_process()
        
        # Record restart result
        success = stop_success and start_success
        self.restart_policy.record_restart(success)
        
        if success:
            self.stats['total_restarts'] += 1
            self._send_notification(f"Server restarted successfully: {reason}", "SUCCESS")
        else:
            self.stats['total_failures'] += 1
            self._send_notification(f"Server restart failed: {reason}", "ERROR")
            
        return success
    
    def start_monitoring(self):
        """Start health monitoring in background thread"""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return
            
        logger.info(f"Starting health monitoring (every {self.health_check_interval}s)")
        self.monitoring_active = True
        
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="HTTPServerMonitor"
        )
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop health monitoring"""
        logger.info("Stopping health monitoring")
        self.monitoring_active = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        consecutive_failures = 0
        
        while self.monitoring_active:
            try:
                if self.state in [ServerState.RUNNING, ServerState.UNHEALTHY]:
                    is_healthy = self._check_health()
                    
                    if is_healthy:
                        if self.state == ServerState.UNHEALTHY:
                            logger.info("Server recovered to healthy state")
                            self._send_notification("HTTP Server recovered", "SUCCESS")
                        
                        self.state = ServerState.RUNNING
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                        logger.warning(f"Health check failed (#{consecutive_failures})")
                        
                        if consecutive_failures >= 3:  # 3 consecutive failures
                            logger.error("Server appears unresponsive, attempting restart")
                            self.state = ServerState.UNHEALTHY
                            
                            if self.restart_server("Health check failures"):
                                consecutive_failures = 0
                            else:
                                self.state = ServerState.FAILED
                
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                time.sleep(self.health_check_interval)
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive server status"""
        status = {
            'state': self.state.value,
            'port': self.port,
            'process_id': self.process.pid if self.process else None,
            'process_running': self.process.poll() is None if self.process else False,
            'last_health_check': self.last_health_check,
            'stats': self.stats.copy(),
            'restart_policy': {
                'consecutive_failures': self.restart_policy.consecutive_failures,
                'circuit_open': self.restart_policy.circuit_open,
                'restarts_this_hour': len(self.restart_policy.restart_history)
            }
        }
        
        if self.start_time:
            status['current_uptime'] = time.time() - self.start_time
            
        return status

# Notification and Job Wrapper Functions
def send_telegram_log(message: str, level: str = "INFO", use_markdown: bool = False):
    """Send a log message to Telegram, using Markdown only when safe."""
    prefix_map = {
        "INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", 
        "ERROR": "❌", "START": "🚀", "COMPLETE": "🏁", "HEARTBEAT": "❤️"
    }
    prefix = prefix_map.get(level.upper(), "🔹")
    
    timestamp = datetime.now().strftime('%H:%M:%S')

    try:
        parse_mode = 'MarkdownV2' if use_markdown else None
        
        if parse_mode == 'MarkdownV2':
            # Escape special characters for MarkdownV2
            safe_message = message.replace('.', '\\.').replace('-', '\\-').replace('!', '\\!')
            full_message = f"{prefix} *{level.upper()}* | `{timestamp}`\n{safe_message}"
        else:
             full_message = f"{prefix} {level.upper()} | {timestamp}\n{message}"

        send_telegram_message(full_message, parse_mode=parse_mode)
        logger.info(f"Sent Telegram: {level} - {message[:50]}...")

    except Exception as e:
        logger.warning(f"Telegram notification failed: {e}")
        logger.info(f"Failed message: {level} - {message}")
        
        # Try fallback without markdown
        try:
            fallback_message = f"{prefix} {level.upper()} | {timestamp}\nTelegram fallback: {message}"
            send_telegram_message(fallback_message, parse_mode=None)
            logger.info("Telegram fallback succeeded")
        except Exception as final_e:
            logger.error(f"Complete Telegram failure: {final_e}")

def telegram_job_wrapper(job_name: str):
    """Decorator to log job execution and send Telegram notifications safely."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            monitoring_stats["last_job_time"] = start_time
            
            logging.info(f"Starting job: {job_name}")
            send_telegram_log(f"Starting job: `{job_name}`", "START", use_markdown=True)
            
            try:
                result = func(*args, **kwargs)
                monitoring_stats["jobs_executed"] += 1
                duration = datetime.now() - start_time
                
                logging.info(f"Completed job: {job_name} in {str(duration).split('.')[0]}")
                send_telegram_log(f"Completed job: `{job_name}`\nDuration: {str(duration).split('.')[0]}s", "COMPLETE", use_markdown=True)
                
                return result
                
            except Exception as e:
                monitoring_stats["jobs_failed"] += 1
                duration = datetime.now() - start_time
                
                error_details = traceback.format_exc()
                logging.error(f"Job failed: {job_name} - {str(e)}\n{error_details}")
                
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
        f"Uptime: *{health['uptime_hours']}h*\n"
        f"Memory: `{health['memory_percent']}` | CPU: `{health['cpu_percent']}`\n"
        f"Jobs OK: *{health['jobs_executed']}* | Jobs Failed: *{health['jobs_failed']}*\n"
        f"Registered Jobs: *{enabled_jobs}/{total_jobs}* enabled\n"
        f"{server_text}"
    )
    send_telegram_log(message, "HEARTBEAT", use_markdown=True)

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

# Main Script Execution
if __name__ == "__main__":
    # Command line interface for job management
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "status":
            setup_all_jobs(job_registry)
            print(get_job_status_report())
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
            print("Usage:")
            print("  python scheduler.py                  # Run scheduler")
            print("  python scheduler.py status           # Show job status")
            print("  python scheduler.py list             # List all jobs")
            print("  python scheduler.py disable <job>    # Disable job")
            print("  python scheduler.py enable <job>     # Enable job")
            print("  python scheduler.py restart-server   # Restart HTTP server")
            sys.exit(1)

    # Main scheduler execution
    try:
        # Startup sequence
        logger.info("Hunter Scheduler v2.0 starting up with Job Registry...")
        
        # Give systems a moment to initialize before first Telegram message
        time.sleep(2)
        
        send_telegram_log("Hunter Scheduler v2.0 starting up with Job Registry...", "SUCCESS", use_markdown=True)
        
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
        logger.info("Scheduler stopped by user.")
        graceful_shutdown()
        send_telegram_log("Scheduler stopped manually.", "WARNING")
    
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