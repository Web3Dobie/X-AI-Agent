# process_http_manager.py - Process-Based HTTP Server Management
import os
import sys
import time
import signal
import socket
import requests
import subprocess
import threading
import psutil
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

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
                logger.warning(f"🔴 Circuit breaker open until {self.circuit_open_until}")
                return False
            else:
                # Reset circuit breaker
                logger.info("🟢 Circuit breaker reset")
                self.circuit_open = False
                self.consecutive_failures = 0
        
        # Clean old restart history (older than 1 hour)
        one_hour_ago = now - timedelta(hours=1)
        self.restart_history = [r for r in self.restart_history if r > one_hour_ago]
        
        # Check restart limit
        if len(self.restart_history) >= self.max_restarts_per_hour:
            logger.error(f"❌ Restart limit reached: {len(self.restart_history)}/{self.max_restarts_per_hour} per hour")
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
            
            # Open circuit breaker if threshold reached
            if self.consecutive_failures >= self.circuit_breaker_threshold:
                self.circuit_open = True
                self.circuit_open_until = now + timedelta(minutes=15)  # 15 min circuit breaker
                logger.error(f"🔴 Circuit breaker OPENED after {self.consecutive_failures} failures")

class ProcessHTTPServer:
    """Process-based HTTP server with health monitoring and graceful restart"""
    
    def __init__(self, port: int = 3001, health_check_interval: int = 30):
        self.port = port
        self.health_check_interval = health_check_interval
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
        """Send notification via the scheduler's telegram system"""
        try:
            # Import here to avoid circular imports
            from scheduler import send_telegram_log
            send_telegram_log(message, level)
        except ImportError:
            logger.warning("Could not send Telegram notification - scheduler not available")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    def start_server_process(self) -> bool:
        """Start HTTP server as separate process"""
        if self.process and self.process.poll() is None:
            logger.warning("⚠️ Server process already running")
            return True
            
        logger.info(f"🚀 Starting HTTP server process on port {self.port}")
        self.state = ServerState.STARTING
        
        try:
            # Create server startup script
            server_script = self._create_server_script()
            
            # Start process
            self.process = subprocess.Popen([
                sys.executable, server_script
            ], 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            env=os.environ.copy(),
            preexec_fn=os.setsid if os.name != 'nt' else None  # Process group for clean shutdown
            )
            
            logger.info(f"📡 Server process started with PID: {self.process.pid}")
            self.start_time = time.time()
            self.stats['total_starts'] += 1
            
            # Wait for server to become healthy
            if self._wait_for_healthy(timeout=30):
                self.state = ServerState.RUNNING
                self._send_notification(f"HTTP Server started successfully on port {self.port}", "SUCCESS")
                return True
            else:
                logger.error("❌ Server failed to become healthy")
                self.state = ServerState.FAILED
                self._cleanup_process()
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to start server process: {e}")
            self.state = ServerState.FAILED
            self._send_notification(f"HTTP Server failed to start: {str(e)}", "ERROR")
            return False
    
    def _create_server_script(self) -> str:
        """Create a temporary script to run the HTTP server"""
        script_content = f'''#!/usr/bin/env python3
import sys
import os

# Add the project root to Python path
project_root = "{os.path.dirname(os.path.abspath(__file__))}"
sys.path.insert(0, project_root)

# Import and start the server
from http_server import start_crypto_news_server

if __name__ == "__main__":
    try:
        start_crypto_news_server(port={self.port})
    except KeyboardInterrupt:
        print("Server stopped by signal")
    except Exception as e:
        print(f"Server error: {{e}}")
        sys.exit(1)
'''
        
        script_path = os.path.join(os.path.dirname(__file__), 'temp_server_launcher.py')
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        return script_path
    
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
            logger.info("🔹 No server process to stop")
            return True
            
        logger.info(f"🛑 Stopping server process (PID: {self.process.pid})")
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
                logger.info("✅ Server stopped gracefully")
                return True
            except subprocess.TimeoutExpired:
                logger.warning("⚠️ Graceful shutdown timeout, forcing kill")
                if os.name != 'nt':
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                else:
                    self.process.kill()
                self.process.wait()
                return True
                
        except Exception as e:
            logger.error(f"❌ Error stopping server: {e}")
            return False
        finally:
            self._cleanup_process()
    
    def _cleanup_process(self):
        """Clean up process resources"""
        if self.process:
            try:
                # Clean up temp script
                script_path = os.path.join(os.path.dirname(__file__), 'temp_server_launcher.py')
                if os.path.exists(script_path):
                    os.remove(script_path)
            except Exception as e:
                logger.debug(f"Cleanup warning: {e}")
            
            self.process = None
        
        if self.start_time:
            self.stats['uptime_seconds'] += time.time() - self.start_time
            self.start_time = None
    
    def restart_server(self, reason: str = "Manual restart") -> bool:
        """Restart server with backoff policy"""
        logger.info(f"🔄 Restart requested: {reason}")
        self.stats['last_restart_reason'] = reason
        
        if not self.restart_policy.can_restart():
            logger.error("❌ Restart denied by policy")
            self.stats['total_failures'] += 1
            return False
        
        # Calculate backoff delay
        delay = self.restart_policy.get_backoff_delay()
        if delay > 0:
            logger.info(f"⏳ Waiting {delay}s before restart (backoff policy)")
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
            logger.warning("⚠️ Monitoring already active")
            return
            
        logger.info(f"👁️ Starting health monitoring (every {self.health_check_interval}s)")
        self.monitoring_active = True
        
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="HTTPServerMonitor"
        )
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop health monitoring"""
        logger.info("🛑 Stopping health monitoring")
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
                            logger.info("💚 Server recovered to healthy state")
                            self._send_notification("HTTP Server recovered", "SUCCESS")
                        
                        self.state = ServerState.RUNNING
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                        logger.warning(f"💔 Health check failed (#{consecutive_failures})")
                        
                        if consecutive_failures >= 3:  # 3 consecutive failures
                            logger.error("❌ Server appears unresponsive, attempting restart")
                            self.state = ServerState.UNHEALTHY
                            
                            if self.restart_server("Health check failures"):
                                consecutive_failures = 0
                            else:
                                self.state = ServerState.FAILED
                
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"❌ Monitor loop error: {e}")
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
    
    def __enter__(self):
        """Context manager entry"""
        self.start_server_process()
        self.start_monitoring()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop_monitoring()
        self.stop_server()