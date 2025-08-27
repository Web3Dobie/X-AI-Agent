# utils/tg_notifier.py (Corrected)
import os
import requests

TOKEN   = os.getenv('TG_BOT_TOKEN')
CHAT_ID = os.getenv('TG_CHAT_ID')

def send_telegram_message(text: str, parse_mode: str = None):
    """
    Sends a message to your Telegram chat.
    Args:
        text (str): The message content.
        parse_mode (str, optional): The parse mode ('MarkdownV2' or 'HTML'). 
                                    Defaults to None (plain text).
    """
    if not TOKEN or not CHAT_ID:
        print("ERROR: Telegram credentials (TG_BOT_TOKEN, TG_CHAT_ID) are not set.")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    payload = {
        'chat_id': CHAT_ID,
        'text': text
    }
    
    if parse_mode in ['MarkdownV2', 'HTML']:
        payload['parse_mode'] = parse_mode
        
    try:
        resp = requests.post(url, data=payload, timeout=10)
        resp.raise_for_status() # Raise an exception for HTTP error codes
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to send Telegram message: {e}")
        # You could add a fallback log here if needed