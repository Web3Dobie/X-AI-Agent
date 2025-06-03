import logging
import os
import re
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pandas_ta as ta
import requests

from utils import (TA_POST_DIR, generate_gpt_text, log_substack_post_to_notion)

# Configure logging
log_file = os.path.join(TA_POST_DIR, "ta_substack_generator.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def slugify(text: str) -> str:
    return re.sub(r"\W+", "-", text.lower()).strip("-")


# Token‐market symbols mapping
TOKENS = {
    "bitcoin": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "solana": "SOLUSDT",
    "ripple": "XRPUSDT",
    "dogecoin": "DOGEUSDT",
}

# Define directories
CHART_DIR = os.path.join(TA_POST_DIR, "charts")
os.makedirs(CHART_DIR, exist_ok=True)
os.makedirs(TA_POST_DIR, exist_ok=True)


def fetch_ohlcv(symbol: str, limit: int = 365) -> pd.DataFrame:
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": "1d", "limit": limit}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = pd.DataFrame(
        resp.json(),
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "qav",
            "num_trades",
            "taker_base",
            "taker_quote",
            "ignore",
        ],
    )
    data["date"] = pd.to_datetime(data["open_time"], unit="ms")
    data.set_index("date", inplace=True)
    return data[["open", "high", "low", "close", "volume"]].astype(float)


def generate_static_chart(df: pd.DataFrame, token_label: str) -> str:
    sma50 = df["close"].rolling(50).mean()
    sma200 = df["close"].rolling(200).mean()

    plt.figure(figsize=(10, 4))
    plt.plot(df["close"], label="Close")
    plt.plot(sma50, linestyle="--", label="50D MA")
    plt.plot(sma200, linestyle=":", label="200D MA")
    plt.title(f"{token_label} Price & Moving Averages")
    plt.legend()
    plt.tight_layout()

    path = os.path.join(CHART_DIR, f"{token_label.lower()}_weekly.png")
    plt.savefig(path)
    plt.close()

    return path


def generate_ta_substack_article() -> str:
    logging.info("🔍 Starting TA Substack article generation")
    data_summary = []
    img_paths = []

    for name, symbol in TOKENS.items():
        token_label = name.title()
        df = fetch_ohlcv(symbol)

        # Generate and store the static chart PNG
        chart_path = generate_static_chart(df, token_label)
        img_paths.append(chart_path)

        # Compute latest close, moving averages, and RSI
        latest = df["close"].iloc[-1]
        sma50 = df["close"].rolling(50).mean().iloc[-1]
        sma200 = df["close"].rolling(200).mean().iloc[-1]
        rsi_val = ta.rsi(df["close"], length=14).iloc[-1]

        data_summary.append((token_label, symbol[:-4], latest, sma50, sma200, rsi_val))

    # Build date string and summary bullet points
    date_str = datetime.utcnow().strftime("%B %d, %Y")
    summary_lines = "\n".join(
        f"- {n} (${t}): Close={v:.2f}, 50D MA={s50:.2f}, 200D MA={s200:.2f}, RSI={r:.1f}"
        for n, t, v, s50, s200, r in data_summary
    )

    # Build per‐token sections (chart embed only)
    sections = ""
    for (n, t, v, s50, s200, r), img in zip(data_summary, img_paths):
        sections += (
            f"## {n} (${t})\n"
            f"![Chart]({img})\n\n"
        )

    # The static headline for this weekly column
    headline = "Weekly Technical Analysis for Bitcoin, Ethereum, Solana, XRP, and Dogecoin: A Dobie's Deep Dive"

    # Compose the GPT prompt
    prompt = f"""
You are Hunter the Web3 Dobie 🐾 — a seasoned crypto analyst and educator.

Write a detailed 4,000–5,000 word Substack article titled:
"{headline}"

Include data summary:
{summary_lines}

Structure the article per token:
{sections}

Conclude with cross-token insights, actionable tips, and a reminder to follow @Web3_Dobie. As always, this is NFA — Hunter 🐾.

Today is {date_str}.
"""

    # Generate the GPT‐written Markdown article body
    article_body = generate_gpt_text(prompt, max_tokens=6500)

    # If article_body already starts with the exact same "# <headline>" line, do NOT prepend again
    article_lines = article_body.splitlines()
    if article_lines and article_lines[0].strip() == f"# {headline}":
        full_md = article_body
    else:
        full_md = f"# {headline}\n\n{article_body}"

    # Slugify date and build filename
    slug = slugify(f"weekly-ta-{date_str}")
    sanitized_date = date_str.replace(" ", "_")
    filename = os.path.join(TA_POST_DIR, f"{sanitized_date}_{slug}.md")

    # Write to disk
    with open(filename, "w", encoding="utf-8") as f:
        f.write(full_md)
    logging.info(f"📝 TA Substack article written to {filename}")

    # Log to Notion
    try:
        # Use the first line ("# <headline>") as the Notion title
        log_substack_post_to_notion(f"# {headline}", filename)
        logging.info("✅ Logged TA article to Notion")
    except Exception as e:
        logging.error(f"❌ Notion logging failed: {e}")

    return filename


if __name__ == "__main__":
    path = generate_ta_substack_article()
    print(f"✅ Generated Substack article at {path}")
