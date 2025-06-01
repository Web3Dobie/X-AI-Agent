"""
Text utility functions for tweet content:
- extract_ticker: finds tickers by symbol or name
- insert_cashtags: transforms known tickers into $CASHTAG format.
- insert_mentions: appends relevant Twitter handles based on keywords.
"""

import re

# Map full coin names to tickers
NAME_TO_TICKER = {
    "bitcoin":  "BTC",
    "ethereum": "ETH",
    "ripple":   "XRP",
    "cardano":  "ADA",
    "solana":   "SOL",
    "dogecoin": "DOGE",
    "polkadot": "DOT",
    "uniswap":  "UNI",
    "cosmos":   "ATOM",
    "sui":      "SUI",
}

# Reverse map for quick lookup of valid tickers
VALID_TICKERS = set(NAME_TO_TICKER.values())

# Extend for any explicit symbols you want auto-cashtagged
KNOWN_TICKERS = list(VALID_TICKERS) + ["LINK", "AVAX", "TON"]


def extract_ticker(headline: str) -> str:
    """
    1) Look for explicit all-caps symbols (2–5 letters).
    2) If none, scan for known coin names (case-insensitive).
    3) Default to "Crypto".
    """
    # A) all-caps candidates
    candidates = re.findall(r"\b[A-Z]{2,5}\b", headline)
    for tok in candidates:
        if tok in VALID_TICKERS:
            return tok

    # B) name lookup
    lower = headline.lower()
    for name, ticker in NAME_TO_TICKER.items():
        if name in lower:
            return ticker

    return "Crypto"


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
        "Solana":   "@solana",
        "Dogecoin": "@dogecoin",
        "XRP":      "@Ripple",
        "Coinbase": "@coinbase",
        "Binance":  "@binance",
        "Avalanche":"@avax",
        "Polygon":  "@0xPolygon",
        "Cardano":  "@Cardano",
        "Tezos":    "@tezos",
    }
    for keyword, handle in mention_tags.items():
        if keyword.lower() in text.lower() and handle not in text:
            text += f" {handle}"
    return text
