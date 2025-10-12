# hunter_http_server.py - Enhanced with comment caching

import json
import logging
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

from services.database_service import DatabaseService
from services.hunter_ai_service import get_hunter_ai_service
from utils.url_helpers import get_tweet_url

logger = logging.getLogger(__name__)

class HunterNewsHandler(BaseHTTPRequestHandler):
    # Class-level cache (shared across all requests)
    _comment_cache = {}
    _cache_ttl = 300  # 5 minutes
    
    def __init__(self, *args, **kwargs):
        self.db_service = DatabaseService()
        self.hunter_ai = get_hunter_ai_service()
        super().__init__(*args, **kwargs)
    
    @classmethod
    def get_cached_comment(cls, headline):
        """Get cached comment or return None if expired/missing"""
        cache_key = headline
        now = time.time()
        
        if cache_key in cls._comment_cache:
            cached_comment, cached_time = cls._comment_cache[cache_key]
            if now - cached_time < cls._cache_ttl:
                logger.debug(f"Cache hit for headline: {headline[:50]}...")
                return cached_comment
            else:
                # Expired, remove from cache
                del cls._comment_cache[cache_key]
        
        return None
    
    @classmethod
    def set_cached_comment(cls, headline, comment):
        """Store comment in cache with timestamp"""
        cls._comment_cache[headline] = (comment, time.time())
        logger.debug(f"Cached comment for: {headline[:50]}...")
    
    def generate_comment_with_fallback(self, headline):
        """Generate comment with caching and error handling"""
        # Check cache first
        cached = self.get_cached_comment(headline)
        if cached:
            return cached
        
        # Generate new comment
        try:
            comment = self.hunter_ai.generate_headline_comment(headline)
            self.set_cached_comment(headline, comment)
            return comment
        except Exception as e:
            logger.error(f"AI failed for headline '{headline[:50]}...': {e}")
            fallback = "📈 Analysis pending. — Hunter 🐾"
            # Don't cache fallback comments
            return fallback
    
    def do_GET(self):
        if self.path == '/crypto-news-data':
            try:
                headlines = self.db_service.get_recent_headlines_for_display(count=4, hours=2)
                
                formatted_headlines = []
                for h in headlines:
                    comment = self.generate_comment_with_fallback(h['headline'])
                    
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
        
        elif self.path == '/api/latest-tweet':
            # ... existing code ...
            try:
                # Query the latest tweet from content_log
                with self.db_service.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT 
                                content_type,
                                tweet_id,
                                details,
                                created_at
                            FROM hunter_agent.content_log
                            WHERE tweet_id IS NOT NULL
                            ORDER BY created_at DESC
                            LIMIT 1
                        """)
                        result = cur.fetchone()
                
                if not result:
                    self._send_error(404, "No tweets found")
                    return
                
                content_type, tweet_id, details, created_at = result
                
                # Calculate "time ago"
                now = datetime.utcnow()
                if created_at.tzinfo is not None:
                    created_at = created_at.replace(tzinfo=None)
                
                delta = now - created_at
                if delta.days > 0:
                    time_ago = f"{delta.days}d ago"
                elif delta.seconds >= 3600:
                    time_ago = f"{delta.seconds // 3600}h ago"
                elif delta.seconds >= 60:
                    time_ago = f"{delta.seconds // 60}m ago"
                else:
                    time_ago = "just now"
                
                # Truncate text for preview (150 chars)
                preview_text = details[:150] + "..." if len(details) > 150 else details
                
                # Construct tweet URL
                tweet_url = get_tweet_url("Web3_Dobie", tweet_id)
                
                response = {
                    "success": True,
                    "data": {
                        "id": tweet_id,
                        "text": preview_text,
                        "fullText": details,
                        "type": content_type,
                        "createdAt": created_at.isoformat(),
                        "timeAgo": time_ago,
                        "url": tweet_url,
                        "user": {
                            "id": "web3_dobie",
                            "username": "Web3_Dobie",
                            "name": "Web3 Dobie"
                        }
                    }
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode('utf-8'))
                
            except BrokenPipeError:
                return
            except Exception as e:
                logger.error(f"Error fetching latest tweet: {e}", exc_info=True)
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