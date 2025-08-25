# http_server.py - Enhanced with heartbeat monitoring
"""
Enhanced HTTP server for crypto news data with comprehensive monitoring
"""

import json
import os
import time
import threading
import psutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone
from utils.config import DATA_DIR
from utils.logging_helper import get_module_logger
from utils.tg_notifier import send_telegram_message

logger = get_module_logger(__name__)

class CryptoNewsHandler(BaseHTTPRequestHandler):
    # Track server statistics
    request_count = 0
    last_request_time = None
    start_time = time.time()
    
    def do_GET(self):
        start_request_time = time.time()
        CryptoNewsHandler.request_count += 1
        CryptoNewsHandler.last_request_time = start_request_time
        
        if self.path == '/crypto-news-data':
            try:
                json_file = os.path.join(DATA_DIR, 'crypto_news_api.json')
                
                if os.path.exists(json_file):
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = f.read()
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')  # Enable CORS
                    self.end_headers()
                    self.wfile.write(data.encode('utf-8'))
                    
                    response_time = (time.time() - start_request_time) * 1000  # ms
                    logger.info(f"✅ Served crypto news data via HTTP ({response_time:.1f}ms)")
                else:
                    # Return empty but valid response
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    
                    empty_response = {
                        "success": True,
                        "data": [],
                        "message": "No crypto news data available yet"
                    }
                    self.wfile.write(json.dumps(empty_response).encode('utf-8'))
                    logger.warning("⚠️ Crypto news data file not found, returned empty response")
                    
            except Exception as e:
                logger.error(f"❌ Error serving crypto news data: {e}")
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                
                error_response = {
                    "success": False,
                    "error": "Internal server error"
                }
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
                
        elif self.path == '/health':
            # Health check endpoint
            try:
                health_data = self._get_health_status()
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(health_data).encode('utf-8'))
                
                logger.debug("🏥 Health check served")
                
            except Exception as e:
                logger.error(f"❌ Health check failed: {e}")
                self.send_response(500)
                self.end_headers()
                
        else:
            self.send_response(404)
            self.end_headers()
    
    def _get_health_status(self):
        """Get comprehensive server health status"""
        uptime = time.time() - CryptoNewsHandler.start_time
        
        # Get system resources
        try:
            memory_usage = psutil.virtual_memory().percent
            cpu_usage = psutil.cpu_percent()
        except:
            memory_usage = 0
            cpu_usage = 0
        
        # Check data file
        json_file = os.path.join(DATA_DIR, 'crypto_news_api.json')
        data_file_status = {
            "exists": os.path.exists(json_file),
            "size": os.path.getsize(json_file) if os.path.exists(json_file) else 0,
            "modified": datetime.fromtimestamp(os.path.getmtime(json_file)).isoformat() if os.path.exists(json_file) else None
        }
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": round(uptime, 1),
            "requests_served": CryptoNewsHandler.request_count,
            "last_request": datetime.fromtimestamp(CryptoNewsHandler.last_request_time).isoformat() if CryptoNewsHandler.last_request_time else None,
            "system": {
                "memory_usage_percent": memory_usage,
                "cpu_usage_percent": cpu_usage
            },
            "data_file": data_file_status
        }
    
    def log_message(self, format, *args):
        # Suppress default HTTP server logs (we use our own logger)
        pass

class MonitoredHTTPServer:
    """HTTP Server wrapper with monitoring capabilities"""
    
    def __init__(self, port=3001):
        self.port = port
        self.server = None
        self.monitoring_thread = None
        self.running = False
        self.last_health_check = time.time()
        
    def start_server(self):
        """Start the HTTP server with monitoring"""
        try:
            server_address = ('', self.port)
            self.server = HTTPServer(server_address, CryptoNewsHandler)
            self.running = True
            
            logger.info(f"🌐 Starting crypto news HTTP server on port {self.port}")
            print(f"🌐 Crypto news server running on http://localhost:{self.port}/crypto-news-data")
            
            # Start monitoring in background thread
            self.monitoring_thread = threading.Thread(target=self._monitor_server, daemon=True)
            self.monitoring_thread.start()
            
            # Send startup notification
            self._send_server_notification("🚀 HTTP Server Started", "healthy")
            
            # Start the server (this blocks)
            self.server.serve_forever()
            
        except Exception as e:
            logger.error(f"❌ Failed to start HTTP server: {e}")
            self._send_server_notification(f"💥 HTTP Server Failed", f"error: {e}")
            raise
    
    def _monitor_server(self):
        """Monitor server health and send periodic heartbeats"""
        while self.running:
            try:
                current_time = time.time()
                
                # Send heartbeat every 15 minutes
                if current_time - self.last_health_check > 900:  # 15 minutes
                    self._send_health_heartbeat()
                    self.last_health_check = current_time
                
                # Sleep for 30 seconds before next check
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ Server monitoring error: {e}")
                time.sleep(60)  # Wait longer if there's an error
    
    def _send_health_heartbeat(self):
        """Send detailed health heartbeat to Telegram"""
        try:
            # Test server responsiveness
            import urllib.request
            import urllib.error
            
            test_start = time.time()
            try:
                with urllib.request.urlopen(f'http://localhost:{self.port}/health', timeout=5) as response:
                    health_data = json.loads(response.read().decode())
                response_time = (time.time() - test_start) * 1000  # ms
                server_responsive = True
            except Exception as e:
                response_time = (time.time() - test_start) * 1000
                server_responsive = False
                health_data = {"error": str(e)}
            
            # Get system stats
            try:
                memory_usage = psutil.virtual_memory().percent
                cpu_usage = psutil.cpu_percent()
                disk_usage = psutil.disk_usage('/').percent
            except:
                memory_usage = cpu_usage = disk_usage = 0
            
            # Build heartbeat message
            status_emoji = "💚" if server_responsive else "💔"
            uptime = time.time() - CryptoNewsHandler.start_time
            uptime_hours = uptime / 3600
            
            heartbeat_msg = (
                f"{status_emoji} **HTTP Server Heartbeat**\n"
                f"🌐 Port: {self.port}\n"
                f"⏱️ Uptime: {uptime_hours:.1f}h\n"
                f"📊 Requests: {CryptoNewsHandler.request_count}\n"
                f"🚀 Response: {response_time:.1f}ms\n"
                f"💾 Memory: {memory_usage:.1f}%\n"
                f"🔥 CPU: {cpu_usage:.1f}%\n"
                f"💿 Disk: {disk_usage:.1f}%"
            )
            
            if not server_responsive:
                heartbeat_msg += f"\n❌ **SERVER NOT RESPONSIVE**: {health_data.get('error', 'Unknown error')}"
            
            send_telegram_message(heartbeat_msg)
            logger.info(f"💓 Sent HTTP server heartbeat (responsive: {server_responsive})")
            
        except Exception as e:
            logger.error(f"❌ Failed to send server heartbeat: {e}")
    
    def _send_server_notification(self, title: str, status: str):
        """Send server status notification to Telegram"""
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            message = f"🌐 **{title}**\n⏰ {timestamp}\n📡 Port: {self.port}\n📊 Status: {status}"
            send_telegram_message(message)
        except Exception as e:
            logger.error(f"❌ Failed to send server notification: {e}")
    
    def stop_server(self):
        """Stop the server and monitoring"""
        self.running = False
        if self.server:
            self.server.shutdown()
            self._send_server_notification("🛑 HTTP Server Stopped", "shutdown")

def start_crypto_news_server(port=3001):
    """Start the monitored HTTP server for crypto news data"""
    server = MonitoredHTTPServer(port)
    server.start_server()

if __name__ == "__main__":
    start_crypto_news_server()