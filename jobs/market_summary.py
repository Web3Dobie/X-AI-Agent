# Hunter-Agent/jobs/market_summary.py

import logging
import os
import requests
from datetime import datetime

# No longer needs DatabaseService
from services.ai_service import get_ai_service
from utils.x_post import post_thread, upload_media

logger = logging.getLogger(__name__)

# --- Helper function for this job ---
def _get_market_summary_data():
    """Fetches simple price and 24h change from a live API."""
    tokens = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL", "ripple": "XRP", "dogecoin": "DOGE"}
    try:
        ids = ",".join(tokens.keys())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = []
        for name, ticker in tokens.items():
            info = data.get(name, {})
            if "usd" in info and "usd_24h_change" in info:
                results.append({"ticker": ticker, "price": info["usd"], "change": info["usd_24h_change"]})
        
        if len(results) < 3: return []
        
        all_negative = all(t['change'] < 0 for t in results)
        results.sort(key=lambda x: x['change'], reverse=not all_negative)
        return results
    except Exception as e:
        logger.error(f"Error fetching market summary prices: {e}")
        return []

# --- The New Job Function (Corrected Version) ---
def run_market_summary_job():
    """
    Generates and posts a daily market summary thread using live data.
    This job does NOT write to the database.
    """
    logger.info("📈 Starting Market Summary Job...")
    ai_service = get_ai_service()

    try:
        # 1. Fetch live market data
        tokens_data = _get_market_summary_data()
        if not tokens_data:
            logger.warning("Not enough token data to generate a summary. Skipping.")
            return

        # 2. Generate thread content using the AI Service
        bullet_points = " ".join(f"${t['ticker']}: ${t['price']:,.2f} ({t['change']:+.2f}%)" for t in tokens_data)
        task_rules = """
**TASK:** Write a clever, insightful tweet for each token in the data block below.
**RULES:**
- Each tweet must include the exact price and 24h change.
- Maintain a confident, expert tone. Avoid hype.
- End each tweet with '— Hunter 🐾'.
- Separate each tweet with '---'.
"""
        thread_parts = ai_service.generate_thread(
            prompt=bullet_points, system_instruction=task_rules, parts=len(tokens_data), max_tokens=3000
        )

        if not thread_parts or len(thread_parts) < len(tokens_data):
            logger.warning("AI returned insufficient parts for the market summary. Skipping.")
            return

        # 3. Prepare and post the thread
        today = datetime.utcnow().strftime("%Y-%m-%d")
        header = f"Daily Dobie Market Update [{today}] 📅\n\n"
        thread_parts[0] = header + thread_parts[0]

        leading_token = tokens_data[0]['ticker']
        all_negative = all(t['change'] < 0 for t in tokens_data)
        image_type = "down" if all_negative else "up"
        
        token_images = {
            "BTC": {"up": "/app/content/assets/hunter_poses/BTC_up.png", "down": "/app/content/assets/hunter_poses/BTC_down.png"},
            "ETH": {"up": "/app/content/assets/hunter_poses/ETH_up.png", "down": "/app/content/assets/hunter_poses/ETH_down.png"},
            "SOL": {"up": "/app/content/assets/hunter_poses/SOL_up.png", "down": "/app/content/assets/hunter_poses/SOL_down.png"},
            "XRP": {"up": "/app/content/assets/hunter_poses/XRP_up.png", "down": "/app/content/assets/hunter_poses/XRP_down.png"},
            "DOGE": {"up": "/app/content/assets/hunter_poses/DOGE_up.png", "down": "/app/content/assets/hunter_poses/DOGE_down.png"}
        }
        image_path = token_images.get(leading_token, {}).get(image_type)
        media_id = upload_media(image_path) if image_path and os.path.exists(image_path) else None

        post_result = post_thread(thread_parts, category="market_summary", media_id_first=media_id)
        
        # Database logging
        if post_result and post_result.get("error") is None:
            logger.info("✅ Market summary thread posted successfully.")
            final_tweet_id = post_result.get("final_tweet_id")
            full_thread_text = "\n---\n".join(thread_parts)
    
            db_service.log_content(
                content_type="market_summary", 
                tweet_id=final_tweet_id,
                details=full_thread_text, 
                headline_id=None, 
                ai_provider=ai_service.provider.value
            )
            
            # Decrement rate limiter for each tweet in the thread
            from utils.rate_limit_manager import decrement_rate_limit_counter
            for i in range(len(thread_parts)):
                decrement_rate_limit_counter()
            
            logger.info(f"✅ Logged market summary and decremented rate limiter by {len(thread_parts)}")
        else:
            logger.error(f"Failed to post market summary thread. Error: {post_result.get('error')}")

    except Exception as e:
        logger.error(f"❌ Failed to complete market summary job: {e}", exc_info=True)
        raise