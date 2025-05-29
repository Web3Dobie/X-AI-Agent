"""
Text utility functions for tweet content:
- insert_cashtags: transforms known tickers into $CASHTAG format.
- insert_mentions: appends relevant Twitter handles based on keywords.
"""

import re

# You can extend this list via environment variable or config if needed.
KNOWN_TICKERS = ["BTC", "ETH", "SOL", "DOGE", "AVAX", "ADA", "XRP", "LINK", "TON"]


def insert_cashtags(text: str) -> str:
    """
    Prefixes standalone occurrences of known tickers with '$'.
    """
    for ticker in KNOWN_TICKERS:
        pattern = r"(?<!\$)\b" + re.escape(ticker) + r"\b"
        text = re.sub(pattern, f"${ticker}", text, flags=re.IGNORECASE)
    return text


def insert_mentions(text: str) -> str:
    """
    Appends relevant @mentions based on keywords in the text.
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
        "Tezos": "@tezos",
    }
    added = False
    for keyword, handle in mention_tags.items():
        if keyword.lower() in text.lower() and handle not in text:
            text += f" {handle}"
            added = True
    return text
