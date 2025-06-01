"""
Fetches crypto prices, generates a market summary thread via GPT, and posts it to X.
"""

import logging
import os
import time
from datetime import datetime

import requests

from utils import LOG_DIR, generate_gpt_thread, post_thread

# Configure logging
log_file = os.path.join(LOG_DIR, "market_summary.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Token mapping: name -> ticker
TOKENS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL",
    "ripple": "XRP",
    "dogecoin": "DOGE",
}


def get_top_tokens_data():
    """
    Fetch price and 24h change for each token from CoinGecko.
    Returns a list of dicts with 'ticker', 'price', and 'change'.
    """
    try:
        ids = ",".join(TOKENS.keys())
        url = (
            f"https://api.coingecko.com/api/v3/simple/price"
            f"?ids={ids}&vs_currencies=usd&include_24hr_change=true"
        )
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        results = []
        for name, ticker in TOKENS.items():
            info = data.get(name, {})
            price = info.get("usd")
            change = info.get("usd_24h_change")
            if price is None or change is None:
                logging.warning(f"⚠️ Incomplete data for {name}")
                continue
            results.append({"ticker": ticker, "price": price, "change": change})

        if len(results) < 3:
            logging.warning("⚠️ Fewer than 3 valid tokens—skipping.")
            return []

        return results
    except Exception as e:
        logging.error(f"❌ Error fetching prices: {e}")
        return []


def generate_market_summary_thread():
    """
    Build a GPT thread summarizing prices for tracked tokens.
    Returns a list of tweet-part strings.
    """
    tokens_data = get_top_tokens_data()
    if not tokens_data:
        return []

    bullet_points = " ".join(
        f"${t['ticker']}: ${t['price']:,.2f} ({t['change']:+.2f}%)" for t in tokens_data
    )
    prompt = f"""Here’s today’s crypto prices:
{bullet_points}

Write a short, clever tweet for each line above,
including the exact USD price and 24h % change.
Use emojis and end each with '— Hunter 🐾'.
Do NOT number them—just separate by newlines."""
    thread = generate_gpt_thread(prompt, max_parts=len(tokens_data), delimiter="---")
    if not thread or len(thread) < len(tokens_data):
        logging.warning("⚠️ GPT returned insufficient parts.")
        return []

    today = datetime.utcnow().strftime("%Y-%m-%d")
    header = f"Daily Dobie Market Update [{today}] 📅"
    thread[0] = f"{header}" + thread[0]
    return thread


def post_market_summary_thread():
    """
    Attempts to generate and post the market summary thread,
    retrying up to 5 times with delays if generation fails.
    """
    max_attempts = 5
    delay = 900  # seconds (15m)
    start = time.time()

    for i in range(1, max_attempts + 1):
        logging.info(f"📈 Attempt {i} for market summary thread.")
        thread = generate_market_summary_thread()
        if thread:
            post_thread(thread, category="market_summary")
            logging.info("✅ Market summary posted.")
            return
        if time.time() - start < max_attempts * delay:
            logging.warning(f"⚠️ Attempt {i} failed—retrying in {delay//60}m.")
            time.sleep(delay)
        else:
            break
    logging.error("❌ All attempts for market summary thread failed.")
