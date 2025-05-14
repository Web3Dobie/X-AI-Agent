import feedparser
import logging

RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
    "https://cryptoslate.com/feed/",
    "https://bitcoinmagazine.com/feed",
    "https://beincrypto.com/feed/"
]

def fetch_headlines(limit=10):
    headlines = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:limit]:
                title = entry.title.strip()
                link = entry.link.strip()
                headlines.append((title, link))
        except Exception as e:
            logging.warning(f"⚠️ Failed to fetch from {url}: {e}")
    return headlines

def extract_ticker_from_headline(headline):
    headline = headline.lower()
    if "bitcoin" in headline or "btc" in headline:
        return "BTC"
    elif "ethereum" in headline or "eth" in headline:
        return "ETH"
    elif "solana" in headline or "sol" in headline:
        return "SOL"
    elif "xrp" in headline:
        return "XRP"
    elif "dogecoin" in headline or "doge" in headline:
        return "DOGE"
    elif "cardano" in headline or "ada" in headline:
        return "ADA"
    elif "polygon" in headline or "matic" in headline:
        return "MATIC"
    elif "optimism" in headline or "op" in headline:
        return "OP"
    return "CRYPTO"