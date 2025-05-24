import logging
from datetime import datetime
from utils.gpt import generate_gpt_thread
from utils.x_post import post_thread
import requests
import time

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

        if response.status_code != 200:
            logging.error(f"❌ Bad response from CoinGecko: {response.status_code}")
            return []

        data = response.json()
        results = []
        for k, v in TOKENS.items():
            if k not in data or "usd" not in data[k] or "usd_24h_change" not in data[k]:
                logging.warning(f"⚠️ Incomplete price data for {k}")
                continue
            price = data[k]["usd"]
            change = data[k]["usd_24h_change"]
            results.append({"ticker": v, "price": price, "change": change})

        if len(results) < 3:
            logging.warning("⚠️ Fewer than 3 tokens with valid data — skipping this attempt.")
            return []

        return results

    except Exception as e:
        logging.error(f"❌ Error fetching token prices: {e}")
        return []


def generate_market_summary_thread():
    tokens = get_top_tokens_data()
    if not tokens:
        logging.warning("⚠️ No token data available for summary.")
        return []

    bullet_points = "\n".join([
        f"${t['ticker']}: ${t['price']:.2f} ({t['change']:+.2f}%)" for t in tokens
    ])

    if not bullet_points.strip():
        logging.warning("⚠️ No bullet points to send to GPT.")
        return []

    logging.debug(f"🧾 Bullet points for GPT:\n{bullet_points}")

    prompt = f"""
Write short, clever summaries for each of these {len(tokens)} crypto tokens. 
Use a Web3-savvy tone, rich with emojis and wit. End each with '— Hunter 🐾'. Do NOT number them. Do NOT include headers.

{bullet_points}
"""

    blurbs = generate_gpt_thread(prompt, max_parts=len(tokens), delimiter="---")
    if not blurbs or len(blurbs) < len(tokens):
        logging.warning("⚠️ GPT returned insufficient blurbs — skipping this attempt.")
        return []

    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    header = f"Daily Dobie Market Update [{today_str}] 📅\n\n"
    blurbs[0] = header + blurbs[0]
    return blurbs


def post_market_summary_thread():
    max_attempts = 5
    delay_between_attempts = 900  # 15 minutes
    start_time = time.time()

    for attempt in range(1, max_attempts + 1):
        logging.info(f"📈 Attempt {attempt} to generate and post market summary thread.")
        thread = generate_market_summary_thread()

        if thread:
            post_thread(thread, category="market_summary")
            logging.info("✅ Market summary posted successfully.")
            return

        elapsed = time.time() - start_time
        if elapsed < max_attempts * delay_between_attempts:
            logging.warning(f"⚠️ Attempt {attempt} failed—retrying in {delay_between_attempts//60} minutes.")
            time.sleep(delay_between_attempts)
        else:
            break

    logging.error("❌ Failed to post market summary after multiple attempts within the next hour.")

