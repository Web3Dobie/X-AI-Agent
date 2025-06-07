import logging
from utils.tg_notifier import send_telegram_message

class TelegramHandler(logging.Handler):
    """A logging handler that sends ERROR+ records to Telegram."""

    def emit(self, record):
        # Only forward errors and criticals; change to INFO if you like
        if record.levelno >= logging.ERROR:
            try:
                msg = self.format(record)
                send_telegram_message(f"⚠️ *Log {record.levelname}*\n{msg}")
            except Exception:
                # Avoid infinite loops if Telegram is down
                pass
