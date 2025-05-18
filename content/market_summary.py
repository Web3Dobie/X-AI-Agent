import logging
from datetime import datetime
from utils.gpt import generate_gpt_thread
from utils.x_post import post_thread
import requests

TOKENS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL",
    "ripple": "XRP",
    "optimism": "OP"
}

def get_top_tokens_data():
    try:
        ids = ",".join(TOKENS.keys())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"
        response = requests.get(url)
        data = response.json()
        results = []
        for k, v in TOKENS.items():
            price = data[k]["usd"]
            change = data[k]["usd_24h_change"]
            results.append({"ticker": v, "price": price, "change": change})
        return results
    except Exception as e:
        logging.error(f"❌ Error fetching token prices: {e}")
        return []

def generate_market_summary_thread():
    tokens = get_top_tokens_data()
    if not tokens or len(tokens) < 3:
        logging.warning("⚠️ Market thread too short — skipping.")
        return []

    bullet_points = "\n".join([f"${t['ticker']}: ${t['price']:.2f} ({t['change']:+.2f}%)" for t in tokens])
    prompt = f"""
Write short, clever summaries for each of these 5 crypto tokens. 
Use a Web3-savvy tone, rich with emojis and wit. End each with '— Hunter 🐾'. Do NOT number them. Do NOT include headers.

{bullet_points}
"""

    blurbs = generate_gpt_thread(prompt, max_parts=5, delimiter="---")
    if not blurbs or len(blurbs) < 5:
        return []

    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    header = f"Daily Hunter Market Update [{today_str}] 📅\n\n"
    blurbs[0] = header + blurbs[0]
    return blurbs

def post_market_summary_thread():
    thread = generate_market_summary_thread()
    if thread:
        post_thread(thread, category="market_summary")