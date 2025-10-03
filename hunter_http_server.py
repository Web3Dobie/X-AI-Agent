# hunter_http_server.py - Simple HTTP server like HTD agent

import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

from services.database_service import DatabaseService
from services.hunter_ai_service import get_hunter_ai_service

logger = logging.getLogger(__name__)

class HunterNewsHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.db_service = DatabaseService()
        self.hunter_ai = get_hunter_ai_service()  # ← CHANGE THIS
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        if self.path == '/crypto-news-data':
            try:
                headlines = self.db_service.get_recent_headlines_for_display(count=4, hours=2)
                
                formatted_headlines = []
                for h in headlines:
                    try:
                        # ← USE HUNTER-SPECIFIC METHOD
                        comment = self.hunter_ai.generate_headline_comment(h['headline'])
                    except Exception as e:
                        logger.error(f"AI failed: {e}")
                        comment = "📈 Analysis pending. — Hunter 🐾"
                    
                    formatted_headlines.append({
                        "headline": h['headline'],
                        "url": h['url'],
                        "hunterComment": comment
                    })
                
                response = {
                    "success": True,
                    "data": formatted_headlines,
                    "lastUpdated": datetime.now().isoformat()
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                try:
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                except BrokenPipeError:
                    logger.warning("Client disconnected before response completed")
                    return
                
            except BrokenPipeError:
                return
            except Exception as e:
                logger.error(f"Error: {e}")
                try:
                    self._send_error(500, str(e))
                except BrokenPipeError:
                    return
        
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        
        else:
            self._send_error(404, "Not found")
    
    def _send_error(self, code, message):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode())
    
    def log_message(self, format, *args):
        pass

def start_hunter_server(port=3001):
    server = HTTPServer(('0.0.0.0', port), HunterNewsHandler)
    logger.info(f"Hunter server on port {port}")
    server.serve_forever()