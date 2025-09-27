"""
Fetches crypto prices, generates a market summary thread via GPT, and posts it to X.
"""

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from threading import Lock

import requests

from utils import (LOG_DIR, post_thread, get_module_logger, 
                  upload_media) 
from services.ai_service import get_ai_service

logger = get_module_logger(__name__)

# Token mapping: name -> ticker
TOKENS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL",
    "ripple": "XRP",
    "dogecoin": "DOGE",
}

TOKEN_IMAGES = {
    "BTC": {"up": "content/assets/hunter_poses/BTC_up.png", 
            "down": "content/assets/hunter_poses/BTC_down.png"},
    "ETH": {"up": "content/assets/hunter_poses/ETH_up.png", 
            "down": "content/assets/hunter_poses/ETH_down.png"},
    "SOL": {"up": "content/assets/hunter_poses/SOL_up.png", 
            "down": "content/assets/hunter_poses/SOL_down.png"},
    "XRP": {"up": "content/assets/hunter_poses/XRP_up.png", 
            "down": "content/assets/hunter_poses/XRP_down.png"},
    "DOGE": {"up": "content/assets/hunter_poses/DOGE_up.png", 
             "down": "content/assets/hunter_poses/DOGE_down.png"}
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
                logger.warning(f"⚠️ Incomplete data for {name}")
                continue
            results.append({"ticker": ticker, "price": price, "change": change})

        if len(results) < 3:
            logger.warning("⚠️ Fewer than 3 valid tokens—skipping.")
            return []

        # Sort by change percentage (descending for gains, ascending for losses)
        all_negative = all(t['change'] < 0 for t in results)
        results.sort(key=lambda x: x['change'], reverse=not all_negative)

        return results
    except Exception as e:
        logger.error(f"❌ Error fetching prices: {e}")
        return []

# Thread safety lock
_market_summary_lock = Lock()
_last_attempt_time = None

def generate_market_summary_thread():
    """
    Build a Gemini thread summarizing prices for tracked tokens.
    Returns a list of tweet-part strings.
    """

    tokens_data = get_top_tokens_data()
    if not tokens_data:
        logger.warning("⚠️ No valid token data available.")
        return []

    logger.info(f"📊 Fetched prices for {len(tokens_data)} tokens.")

    bullet_points = " ".join(
        f"${t['ticker']}: ${t['price']:,.2f} ({t['change']:+.2f}%)" for t in tokens_data
    )
    prompt = f"""**ROLE:** You are Hunter 🐾, a witty and sharp crypto analyst.

**TASK:** Write a clever, insightful tweet for each token in the data block below.

**RULES:**
- Each tweet must include the exact price and 24h change.
- Use relevant emojis.
- Maintain a confident, expert tone. Avoid hype.
- Do not use hashtags.
- End each tweet with '— Hunter 🐾'.
- Separate each tweet with '---'.

**DATA:**
{bullet_points}
"""

    ai_service = get_ai_service()
    thread = ai_service.generate_thread(prompt, max_parts=len(tokens_data), delimiter="---", max_tokens=2000)
    if not thread or len(thread) < len(tokens_data):
        logger.warning("⚠️ GPT returned insufficient parts.")
        logger.info(f"📝 GPT raw output: {thread}")
        return []

    logger.info(f"📝 GPT returned thread of {len(thread)} parts.")   
    today = datetime.utcnow().strftime("%Y-%m-%d")
    header = f"Daily Dobie Market Update [{today}] 📅\n\n"
    thread[0] = f"{header}" + thread[0]
    return thread


def post_market_summary_thread():
    """
    Attempts to generate and post the market summary thread with appropriate Hunter pose
    based on market sentiment (pointing up for bullish, thinking for bearish).
    retrying up to 5 times with delays if generation fails.
    """

    global _last_attempt_time
    
    # Ensure only one thread can post at a time
    if not _market_summary_lock.acquire(blocking=False):
        logger.warning("⚠️ Another market summary thread is already running")
        return
        
    try:
        # Check if we've attempted recently (within 5 minutes)
        now = datetime.now(timezone.utc)
        if _last_attempt_time and (now - _last_attempt_time) < timedelta(minutes=5):
            logger.warning("⚠️ Skipping market summary - too soon since last attempt")
            return

        _last_attempt_time = now
        max_attempts = 5
        delay = 900  # seconds (15m)
        start = time.time()

        for i in range(1, max_attempts + 1):
            logger.info(f"📈 Attempt {i} for market summary thread.")
            thread = generate_market_summary_thread()
            if thread:
                # Get sorted token data
                tokens_data = get_top_tokens_data()
                if tokens_data:
                    leading_token = tokens_data[0]['ticker']
                    all_negative = all(t['change'] < 0 for t in tokens_data)
                    
                    # Get appropriate image based on leading token and sentiment
                    image_type = "down" if all_negative else "up"
                    image_path = TOKEN_IMAGES[leading_token][image_type]
                    
                    try:
                        media_id = upload_media(image_path)
                        logger.info(f"✅ Uploaded {leading_token}_{image_type} Hunter pose")
                    except Exception as e:
                        logger.error(f"❌ Failed to upload image: {e}")
                        media_id = None
                else:
                    media_id = None

                result = post_thread(thread, category="market_summary", media_id_first=media_id)

                if result["posted"] == result["total"]:
                    logger.info("✅ Posted market summary thread with sentiment-based image")
                else:
                    logger.warning(f"⚠️ Market summary thread incomplete: {result['posted']}/{result['total']} tweets posted (error: {result['error']})")
           
                return

            if time.time() - start < max_attempts * delay:
                logger.warning(f"⚠️ Attempt {i} failed—retrying in {delay//60}m.")
                time.sleep(delay)
            else:
                break
        logger.error("❌ All attempts for market summary thread failed.")

    finally:
        _market_summary_lock.release()
        logger.info("🔒 Market summary lock released.")
