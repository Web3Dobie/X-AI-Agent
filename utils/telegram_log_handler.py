# utils/telegram_log_handler.py - Thread-safe version
import logging
import threading
import time
from typing import Optional
from .tg_notifier import send_telegram_message

class TelegramHandler(logging.Handler):
    """
    Thread-safe logging handler that sends INFO+ records to Telegram.
    Each thread gets its own session to prevent I/O conflicts.
    """
    
    def __init__(self, level=logging.INFO):
        super().__init__(level)
        self._thread_local = threading.local()
        self._last_error_time = 0
        self._error_count = 0
        self._max_errors_per_minute = 5  # Rate limit error logging
        
    def _should_log_error(self) -> bool:
        """Rate limit error logging to prevent spam."""
        current_time = time.time()
        if current_time - self._last_error_time > 60:  # Reset every minute
            self._error_count = 0
            self._last_error_time = current_time
        
        self._error_count += 1
        return self._error_count <= self._max_errors_per_minute

    def emit(self, record):
        """
        Emit a log record to Telegram with thread-safe session handling.
        """
        # Skip if we're hitting too many errors
        if not self._should_log_error():
            return
            
        try:
            # Only forward INFO and above
            if record.levelno >= logging.INFO:
                msg = self.format(record)
                
                # Prefix with emoji based on level
                prefix = {
                    logging.INFO: "ℹ️",
                    logging.WARNING: "⚠️", 
                    logging.ERROR: "❌",
                    logging.CRITICAL: "💥",
                }.get(record.levelno, "🔹")
                
                # Keep it simple - no markdown to avoid parsing issues
                full_message = f"{prefix} Log {record.levelname}\n{msg}"
                
                # Use thread-safe telegram function (which already creates isolated sessions)
                send_telegram_message(full_message, parse_mode=None)
                
        except Exception as e:
            # Don't let Telegram failures crash the app
            # Only log to stderr if we haven't hit our error limit
            if self._should_log_error():
                print(f"TelegramHandler failed: {e}", file=__import__('sys').stderr)
            pass