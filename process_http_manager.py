# process_http_manager.py - Final version
import os
import sys
import time
import signal
import socket
import requests
import subprocess
import tempfile
import threading
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any, Callable

logger = logging.getLogger(__name__)

class ServerState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    UNHEALTHY = "unhealthy"
    RESTARTING = "restarting"
    FAILED = "failed"

class RestartPolicy:
    # ... (This class is fine, no changes needed) ...
    def __init__(self, max_restarts_per_hour: int = 5, base_backoff_seconds: int = 30, max_backoff_seconds: int = 300, circuit_breaker_threshold: int = 3):
        self.max_restarts_per_hour = max_restarts_per_hour; self.base_backoff = base_backoff_seconds; self.max_backoff = max_backoff_seconds; self.circuit_breaker_threshold = circuit_breaker_threshold; self.restart_history = []; self.consecutive_failures = 0; self.circuit_open = False; self.circuit_open_until = None
    def can_restart(self) -> bool:
        now = datetime.now()
        if self.circuit_open:
            if now < self.circuit_open_until: logger.warning(f"Circuit breaker open until {self.circuit_open_until}"); return False
            else: logger.info("Circuit breaker reset"); self.circuit_open = False; self.consecutive_failures = 0
        one_hour_ago = now - timedelta(hours=1); self.restart_history = [r for r in self.restart_history if r > one_hour_ago]
        if len(self.restart_history) >= self.max_restarts_per_hour: logger.error(f"Restart limit reached: {len(self.restart_history)}/{self.max_restarts_per_hour} per hour"); return False
        return True
    def get_backoff_delay(self) -> int:
        if self.consecutive_failures == 0: return 0
        return min(self.base_backoff * (2 ** (self.consecutive_failures - 1)), self.max_backoff)
    def record_restart(self, success: bool = True):
        now = datetime.now()
        self.restart_history.append(now)
        if success: self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            if self.consecutive_failures >= self.circuit_breaker_threshold: self.circuit_open = True; self.circuit_open_until = now + timedelta(minutes=15); logger.error(f"Circuit breaker OPENED after {self.consecutive_failures} failures")

class ProcessHTTPServer:
    """Process-based HTTP server with health monitoring and graceful restart"""
    
    def __init__(self, port: int = 3001, health_check_interval: int = 30, notification_callback: Optional[Callable] = None):
        self.port = port
        self.health_check_interval = health_check_interval
        self.notification_callback = notification_callback
        self.process: Optional[subprocess.Popen] = None
        self.state = ServerState.STOPPED
        self.restart_policy = RestartPolicy()
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitoring_active = False
        self.last_health_check = None
        self.start_time = None
        self.stats = {'total_starts': 0, 'total_restarts': 0, 'total_failures': 0, 'uptime_seconds': 0, 'last_restart_reason': None}
        self._temp_script_path = None

    def _send_notification(self, message: str, level: str = "INFO"):
        if self.notification_callback:
            try: self.notification_callback(message, level)
            except Exception as e: logger.warning(f"Notification callback failed: {e}")
        else: logger.info(f"Notification: {level} - {message}")
    
    def start_server_process(self) -> bool:
        if self.process and self.process.poll() is None: logger.warning("Server process already running"); return True
            
        logger.info(f"Starting HTTP server process on port {self.port}")
        self.state = ServerState.STARTING
        
        try:
            # IMPROVED: Use tempfile for the script
            script_content = f'''#!/usr/bin/env python3
import sys, os
project_root = "{os.path.dirname(os.path.abspath(__file__))}"
sys.path.insert(0, os.path.dirname(project_root)) # Add parent directory to path
try:
    from http_server import start_crypto_news_server
    start_crypto_news_server(port={self.port})
except KeyboardInterrupt: pass
except Exception as e: sys.exit(1)
'''
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir=os.path.dirname(__file__)) as f:
                f.write(script_content)
                self._temp_script_path = f.name
            
            self.process = subprocess.Popen([sys.executable, self._temp_script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, env=os.environ.copy(), preexec_fn=os.setsid if os.name != 'nt' else None)
            
            logger.info(f"Server process started with PID: {self.process.pid}")
            self.start_time = time.time(); self.stats['total_starts'] += 1
            
            if self._wait_for_healthy(timeout=30):
                self.state = ServerState.RUNNING
                self._send_notification(f"HTTP Server started successfully on port {self.port}", "SUCCESS")
                return True
            else:
                logger.error("Server failed to become healthy"); self.state = ServerState.FAILED; self._cleanup_process(); return False
                
        except Exception as e:
            logger.error(f"Failed to start server process: {e}", exc_info=True); self.state = ServerState.FAILED; self._send_notification(f"HTTP Server failed to start: {str(e)}", "ERROR"); return False

    def _wait_for_healthy(self, timeout: int = 30) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._check_health(): return True
            time.sleep(1)
        return False
    
    def _check_health(self) -> bool:
        try:
            if not self.process or self.process.poll() is not None: return False
            with socket.create_connection(("localhost", self.port), timeout=3): pass
            response = requests.get(f'http://localhost:{self.port}/health', timeout=5)
            if response.status_code == 200: self.last_health_check = time.time(); return True
        except Exception: pass
        return False

    def stop_server(self, timeout: int = 10) -> bool:
        if not self.process: logger.info("No server process to stop"); return True
        logger.info(f"Stopping server process (PID: {self.process.pid})"); self.state = ServerState.STOPPED
        try:
            if os.name != 'nt': os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            else: self.process.terminate()
            self.process.wait(timeout=timeout)
            logger.info("Server stopped gracefully")
        except subprocess.TimeoutExpired:
            logger.warning("Graceful shutdown timeout, forcing kill")
            if os.name != 'nt': os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            else: self.process.kill()
            self.process.wait()
        except Exception as e: logger.error(f"Error stopping server: {e}"); return False
        finally: self._cleanup_process()
        return True

    def _cleanup_process(self):
        if self.process: self.process = None
        if self.start_time: self.stats['uptime_seconds'] += time.time() - self.start_time; self.start_time = None
        if self._temp_script_path and os.path.exists(self._temp_script_path):
            try: os.unlink(self._temp_script_path)
            except OSError: pass
            self._temp_script_path = None
    
    # ... (restart_server, start_monitoring, etc. are mostly fine) ...
    def restart_server(self, reason: str = "Manual restart") -> bool:
        logger.info(f"Restart requested: {reason}"); self.stats['last_restart_reason'] = reason
        if not self.restart_policy.can_restart(): logger.error("Restart denied by policy"); self.stats['total_failures'] += 1; return False
        delay = self.restart_policy.get_backoff_delay()
        if delay > 0: logger.info(f"Waiting {delay}s before restart"); self._send_notification(f"Server restart delayed {delay}s", "WARNING"); time.sleep(delay)
        self.state = ServerState.RESTARTING
        stop_success = self.stop_server(); start_success = self.start_server_process(); success = stop_success and start_success
        self.restart_policy.record_restart(success)
        if success: self.stats['total_restarts'] += 1; self._send_notification(f"Server restarted successfully: {reason}", "SUCCESS")
        else: self.stats['total_failures'] += 1; self._send_notification(f"Server restart failed: {reason}", "ERROR")
        return success

    def start_monitoring(self):
        if self.monitoring_active: return
        logger.info(f"Starting health monitoring (every {self.health_check_interval}s)"); self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True, name="HTTPServerMonitor"); self.monitor_thread.start()

    def stop_monitoring(self):
        logger.info("Stopping health monitoring"); self.monitoring_active = False
        if self.monitor_thread: self.monitor_thread.join(timeout=5)

    def _monitor_loop(self):
        consecutive_failures = 0
        while self.monitoring_active:
            time.sleep(self.health_check_interval)
            try:
                if self.state in [ServerState.RUNNING, ServerState.UNHEALTHY]:
                    if self._check_health():
                        if self.state == ServerState.UNHEALTHY: logger.info("Server recovered to healthy state"); self._send_notification("HTTP Server recovered", "SUCCESS")
                        self.state = ServerState.RUNNING; consecutive_failures = 0
                    else:
                        consecutive_failures += 1; logger.warning(f"Health check failed (#{consecutive_failures})")
                        if consecutive_failures >= 3:
                            logger.error("Server unresponsive, attempting restart"); self.state = ServerState.UNHEALTHY
                            if self.restart_server("Health check failures"): consecutive_failures = 0
                            else: self.state = ServerState.FAILED
            except Exception as e: logger.error(f"Monitor loop error: {e}")

    def get_status(self) -> Dict[str, Any]:
        status = {'state': self.state.value, 'port': self.port, 'process_id': self.process.pid if self.process else None, 'process_running': self.process.poll() is None if self.process else False, 'last_health_check': self.last_health_check, 'stats': self.stats.copy(), 'restart_policy': {'consecutive_failures': self.restart_policy.consecutive_failures, 'circuit_open': self.restart_policy.circuit_open, 'restarts_this_hour': len(self.restart_policy.restart_history)}}
        if self.start_time: status['current_uptime'] = time.time() - self.start_time
        return status