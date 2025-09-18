# http_server.py - Fixed version with proper resource management
"""
Enhanced HTTP server for crypto news data with fixed startup and resource issues
"""

import json
import os
import time
import threading
import psutil
import socket
import gc
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone
from utils.config import DATA_DIR
from utils.logging_helper import get_module_logger
from utils.tg_notifier import send_telegram_message
from utils.config import HTTP_HOST, HTTP_PORT

logger = get_module_logger(__name__)

class CryptoNewsHandler(BaseHTTPRequestHandler):
    # Class-level statistics with proper thread safety
    _stats_lock = threading.RLock()
    _request_count = 0
    _last_request_time = None
    _start_time = time.time()
    
    # File caching to reduce I/O
    _file_cache = {}
    _file_cache_time = 0
    _cache_ttl = 30  # 30 seconds cache
    
    @classmethod
    def _get_cached_file_content(cls):
        """Get cached file content with TTL to reduce file I/O"""
        with cls._stats_lock:
            current_time = time.time()
            
            # Check if cache is still valid
            if (current_time - cls._file_cache_time) < cls._cache_ttl and cls._file_cache:
                return cls._file_cache.get('content'), cls._file_cache.get('exists', False)
            
            # Refresh cache
            json_file = os.path.join(DATA_DIR, 'crypto_news_api.json')
            try:
                if os.path.exists(json_file):
                    with open(json_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    cls._file_cache = {'content': content, 'exists': True}
                    cls._file_cache_time = current_time
                    return content, True
                else:
                    cls._file_cache = {'content': None, 'exists': False}  
                    cls._file_cache_time = current_time
                    return None, False
            except Exception as e:
                logger.error(f"❌ Error reading file: {e}")
                return None, False

    def do_GET(self):
        start_request_time = time.time()
        
        with self._stats_lock:
            self._request_count += 1
            self._last_request_time = start_request_time
        
        try:
            if self.path == '/crypto-news-data':
                self._handle_crypto_news_request(start_request_time)
            elif self.path == '/health':
                self._handle_health_request()
            else:
                self.send_response(404)
                self.end_headers()
                
        except Exception as e:
            logger.error(f"❌ Request handling error: {e}")
            self._send_error_response(500, "Internal server error")
    
    def _handle_crypto_news_request(self, start_time):
        """Handle crypto news data request"""
        try:
            content, file_exists = self._get_cached_file_content()
            
            if file_exists and content:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'public, max-age=30')
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
                
                response_time = (time.time() - start_time) * 1000
                logger.info(f"✅ Served crypto news data ({response_time:.1f}ms)")
            else:
                # Return structured empty response
                empty_response = {
                    "success": True,
                    "data": [],
                    "message": "No crypto news data available yet",
                    "lastUpdated": datetime.now(timezone.utc).isoformat()
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(empty_response).encode('utf-8'))
                
                logger.warning("⚠️ Crypto news file not found, returned empty response")
                
        except Exception as e:
            logger.error(f"❌ Error serving crypto news: {e}")
            self._send_error_response(500, "Failed to retrieve crypto news")
    
    def _handle_health_request(self):
        """Handle health check request"""
        try:
            health_data = self._get_health_status()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(health_data).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            self._send_error_response(500, "Health check failed")
    
    def _send_error_response(self, status_code, message):
        """Send standardized error response"""
        try:
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_response = {
                "success": False,
                "error": message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
        except Exception as e:
            logger.error(f"❌ Failed to send error response: {e}")
    
    def _get_health_status(self):
        """Get server health status"""
        uptime = time.time() - self._start_time
        
        # Get system resources safely
        try:
            memory_usage = psutil.virtual_memory().percent
            cpu_usage = psutil.cpu_percent()
        except:
            memory_usage = cpu_usage = 0
        
        # Check data file
        json_file = os.path.join(DATA_DIR, 'crypto_news_api.json')
        data_file_status = {
            "exists": os.path.exists(json_file),
            "size": os.path.getsize(json_file) if os.path.exists(json_file) else 0
        }
        
        if os.path.exists(json_file):
            try:
                data_file_status["modified"] = datetime.fromtimestamp(
                    os.path.getmtime(json_file)
                ).isoformat()
            except:
                data_file_status["modified"] = None
        
        return {
            "status": "healthy",
            "service": "crypto-news",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": round(uptime, 1),
            "requests_served": self._request_count,
            "last_request": datetime.fromtimestamp(self._last_request_time).isoformat() if self._last_request_time else None,
            "system": {
                "memory_usage_percent": memory_usage,
                "cpu_usage_percent": cpu_usage
            },
            "data_file": data_file_status,
            "cache": {
                "age_seconds": time.time() - self._file_cache_time,
                "valid": (time.time() - self._file_cache_time) < self._cache_ttl
            }
        }
    
    def log_message(self, format, *args):
        # Suppress default HTTP server logs
        pass

class StabilizedHTTPServer:
    """HTTP Server with proper startup sequence and resource management"""
    
    def __init__(self, port=3001):
        self.port = port
        self.server = None
        self.monitoring_thread = None
        self.running = False
        self.server_ready = threading.Event()
        
    def start_server(self):
        """Start the HTTP server with proper initialization"""
        try:
            # Create server
            server_address = ('', self.port)
            self.server = HTTPServer(server_address, CryptoNewsHandler)
            
            # Configure socket for stability
            self.server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            self.running = True
            
            logger.info(f"🌐 Starting crypto news HTTP server on port {self.port}")
            
            # Start monitoring thread
            self.monitoring_thread = threading.Thread(
                target=self._monitor_server,
                daemon=True,
                name="CryptoMonitor"
            )
            self.monitoring_thread.start()
            
            # Signal that server is ready
            self.server_ready.set()
            
            # Send startup notification
            send_telegram_message(
                f"🌐 **HTTP Server Started**\n"
                f"📡 Port: {self.port}\n"
                f"🔗 http://localhost:{self.port}/crypto-news-data"
            )
            
            logger.info(f"✅ Server ready on port {self.port}")
            
            # Start serving (this blocks)
            self.server.serve_forever()
            
        except Exception as e:
            logger.error(f"❌ Failed to start server: {e}")
            send_telegram_message(f"💥 **Server Failed**\nPort {self.port}\nError: {str(e)}")
            raise
    
    def wait_for_ready(self, timeout=30):
        """Wait for server to be ready"""
        return self.server_ready.wait(timeout)
    
    def _monitor_server(self):
        """Monitor server health and send periodic updates"""
        # Wait for server to be ready first
        if not self.server_ready.wait(60):
            logger.error("❌ Server ready timeout")
            return
        
        last_heartbeat = time.time()
        last_cleanup = time.time()
        
        while self.running:
            try:
                current_time = time.time()
                
                # Cleanup every 5 minutes
                if current_time - last_cleanup > 300:
                    self._perform_cleanup()
                    last_cleanup = current_time
                
                # Heartbeat every 15 minutes
                # if current_time - last_heartbeat > 900:
                    # self._send_heartbeat()
                    # last_heartbeat = current_time
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"❌ Monitoring error: {e}")
                time.sleep(120)
    
    def _perform_cleanup(self):
        """Perform maintenance cleanup"""
        try:
            # Clear file cache if stale
            with CryptoNewsHandler._stats_lock:
                cache_age = time.time() - CryptoNewsHandler._file_cache_time
                if cache_age > 300:  # 5 minutes
                    CryptoNewsHandler._file_cache.clear()
                    CryptoNewsHandler._file_cache_time = 0
            
            # Force garbage collection
            gc.collect()
            
            logger.debug("🧹 Performed cleanup")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
    
    def _send_heartbeat(self):
        """Send heartbeat with server health"""
        try:
            # Test server responsiveness
            server_responsive = self._test_connectivity()
            
            # Get stats
            uptime = time.time() - CryptoNewsHandler._start_time
            
            # Get system info safely
            try:
                memory_usage = psutil.virtual_memory().percent
                cpu_usage = psutil.cpu_percent()
            except:
                memory_usage = cpu_usage = 0
            
            status_emoji = "💚" if server_responsive else "💔"
            
            heartbeat_msg = (
                f"{status_emoji} **Crypto Server Heartbeat**\n"
                f"📡 Port: {self.port}\n"
                f"⏱️ Uptime: {uptime/3600:.1f}h\n"
                f"📊 Requests: {CryptoNewsHandler._request_count}\n"
                f"💾 Memory: {memory_usage:.1f}%\n" 
                f"🔥 CPU: {cpu_usage:.1f}%\n"
                f"🔍 Status: {'Responsive' if server_responsive else 'Not responding'}"
            )
            
            send_telegram_message(heartbeat_msg)
            logger.info(f"💓 Sent heartbeat (responsive: {server_responsive})")
            
        except Exception as e:
            logger.error(f"❌ Heartbeat failed: {e}")
    
    def _test_connectivity(self):
        """Test if server is responding to connections"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            result = sock.connect_ex(('localhost', self.port))
            sock.close()
            return result == 0
        except:
            return False
    
    def stop_server(self):
        """Stop server with cleanup"""
        logger.info("🛑 Stopping server...")
        self.running = False
        
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        
        # Clear caches
        with CryptoNewsHandler._stats_lock:
            CryptoNewsHandler._file_cache.clear()
        
        send_telegram_message("🛑 **HTTP Server Stopped**\nCleanup completed")

def start_crypto_news_server(host=None, port=None):
    host = host or HTTP_HOST
    port = port or HTTP_PORT
    """Start the crypto news server"""
    server = StabilizedHTTPServer(port)
    server.start_server()

def test_server_connectivity(host=None, port=None, timeout=5):
    host = host or HTTP_HOST
    port = port or HTTP_PORT
    """Test if server port is accepting connections"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
    except:
        return False

if __name__ == "__main__":
    start_crypto_news_server()