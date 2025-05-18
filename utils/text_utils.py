import re

KNOWN_TICKERS = ['BTC', 'ETH', 'SOL', 'DOGE', 'AVAX', 'ADA', 'XRP', 'LINK', 'TON']

def insert_cashtags(text: str) -> str:
    for ticker in KNOWN_TICKERS:
        pattern = r'(?<!\$)\b' + re.escape(ticker) + r'\b'
        text = re.sub(pattern, f'${ticker}', text, flags=re.IGNORECASE)
    return text
