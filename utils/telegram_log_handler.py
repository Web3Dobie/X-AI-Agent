# utils/telegram_log_handler.py - Fixed version without markdown
import logging
from .tg_notifier import send_telegram_message

class TelegramHandler(logging.Handler):
    """A logging handler that sends INFO+ records to Telegram in plain text."""

    def emit(self, record):
        try:
            # Only forward INFO and above (this will catch your [OK], WARN and ERROR logs)
            if record.levelno >= logging.INFO:
                msg = self.format(record)
                # Prefix with an emoji based on level
                prefix = {
                    logging.INFO:    "ℹ️",
                    logging.WARNING: "⚠️",
                    logging.ERROR:   "❌",
                    logging.CRITICAL:"💥",
                }.get(record.levelno, "🔹")
                
                # Send as plain text (no parse_mode) to avoid markdown parsing errors
                full_message = f"{prefix} Log {record.levelname}\n{msg}"
                send_telegram_message(full_message, parse_mode=None)
                
        except Exception as e:
            # Don't let Telegram failures crash your app
            # Optionally log the failure locally
            pass