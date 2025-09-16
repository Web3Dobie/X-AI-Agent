# utils/tg_notifier.py
import os
import requests

TOKEN   = os.getenv('TG_BOT_TOKEN')
CHAT_ID = os.getenv('TG_CHAT_ID')

def send_telegram_message(text: str, parse_mode: str = None):
    """
    Sends a message to your Telegram chat using an isolated network session.
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
        # Use 'with' to create a new, isolated session for this request.
        # This is the key fix to prevent connection conflicts.
        with requests.Session() as session:
            resp = session.post(url, data=payload, timeout=10)
            resp.raise_for_status() # Raise an exception for HTTP error codes
            
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to send Telegram message: {e}")
        # Re-raise the exception so the calling function knows it failed
        raise e