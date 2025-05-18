import re

KNOWN_TICKERS = ['BTC', 'ETH', 'SOL', 'DOGE', 'AVAX', 'ADA', 'XRP', 'LINK', 'TON']

def insert_cashtags(text: str) -> str:
    for ticker in KNOWN_TICKERS:
        pattern = r'(?<!\$)\b' + re.escape(ticker) + r'\b'
        text = re.sub(pattern, f'${ticker}', text, flags=re.IGNORECASE)
    return text

def insert_mentions(text: str) -> str:
    """
    Appends relevant @mentions based on keywords in the tweet content.
    """
    mention_tags = {
        "Ethereum": "@ethereum",
        "Solana": "@solana",
        "Dogecoin": "@dogecoin",
        "XRP": "@Ripple",
        "Coinbase": "@coinbase",
        "Binance": "@binance",
        "Pavel Durov": "@durov",
        "Avalanche": "@avax",
        "Polygon": "@0xPolygon",
        "Cardano": "@Cardano",
        "Tezos": "@tezos"
    }
    for keyword, handle in mention_tags.items():
        if keyword.lower() in text.lower() and handle not in text:
            text += f" {handle}"
    return text
