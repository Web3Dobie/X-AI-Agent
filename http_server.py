# http_server.py - Add to X-AI-Agent root directory
"""
Simple HTTP server to serve crypto news data to the containerized website
"""

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from utils.config import DATA_DIR
from utils.logging_helper import get_module_logger

logger = get_module_logger(__name__)

class CryptoNewsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
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
                    logger.info("✅ Served crypto news data via HTTP")
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
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default HTTP server logs (we use our own logger)
        pass

def start_crypto_news_server(port=3001):
    """Start the HTTP server for crypto news data"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, CryptoNewsHandler)
    
    logger.info(f"🌐 Starting crypto news HTTP server on port {port}")
    print(f"🌐 Crypto news server running on http://localhost:{port}/crypto-news-data")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("🛑 Crypto news HTTP server stopped")
        httpd.shutdown()

if __name__ == "__main__":
    start_crypto_news_server()