
import os
from pathlib import Path
import pandas as pd
import pandas_ta as ta
import requests
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime
from utils.gpt import generate_gpt_text
from utils.notion_helpers import log_substack_post_to_notion
import re

# slugify function
def slugify(text):
    return re.sub(r'\W+', '-', text.lower()).strip('-')

# Configuration
TOKENS = {
    "bitcoin": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "solana": "SOLUSDT",
    "ripple": "XRPUSDT",
    "optimism": "OPUSDT"
}
CHART_DIR = "substack_posts/charts"
VIDEO_DIR = "substack_posts/videos"
POST_DIR = "substack_posts"

os.makedirs(CHART_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(POST_DIR, exist_ok=True)

def fetch_ohlcv(symbol, limit=365):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&limit={limit}"
    resp = requests.get(url)
    resp.raise_for_status()
    data = pd.DataFrame(resp.json(), columns=[
        "open_time","open","high","low","close","volume","close_time",
        "qav","num_trades","taker_base","taker_quote","ignore"
    ])
    data["date"] = pd.to_datetime(data["open_time"], unit="ms")
    data.set_index("date", inplace=True)
    cols = ["open","high","low","close","volume"]
    return data[cols].astype(float)

def generate_static_chart(df, token_label):
    sma50 = df["close"].rolling(50).mean()
    sma200 = df["close"].rolling(200).mean()
    plt.figure(figsize=(10,4))
    plt.plot(df["close"], label="Close")
    plt.plot(sma50, linestyle="--", label="50D MA")
    plt.plot(sma200, linestyle=":", label="200D MA")
    plt.title(f"{token_label} Price & MAs")
    plt.legend()
    path = f"{CHART_DIR}/{token_label.lower()}_weekly.png"
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path

def generate_animation_mp4(df, token_label):
    df["rsi"] = ta.rsi(df["close"], length=14)
    window = df.tail(90)
    fig, ax = plt.subplots(figsize=(8,4))
    ax.set_title(f"{token_label} RSI (14D)")
    ax.set_ylim(0,100)
    line, = ax.plot([], [], lw=2)

    def init():
        line.set_data([], [])
        return (line,)

    def animate(i):
        x = window.index[:i]
        y = window["rsi"].values[:i]
        line.set_data(x, y)
        return (line,)

    ani = animation.FuncAnimation(
        fig, animate, frames=len(window), init_func=init,
        blit=True, interval=100
    )
    mp4_path = f"{VIDEO_DIR}/{token_label.lower()}_rsi.mp4"
    # Use ffmpeg writer
    Writer = animation.writers['ffmpeg']
    writer = Writer(fps=10, metadata=dict(artist='Dobie'), bitrate=1800)
    ani.save(mp4_path, writer=writer)
    plt.close()
    return mp4_path

def generate_ta_substack_article():
    data_summary = []
    img_paths = []
    video_paths = []
    for name, symbol in TOKENS.items():
        df = fetch_ohlcv(symbol)
        chart = generate_static_chart(df, name.upper())
        img_paths.append(chart)
        video = generate_animation_mp4(df, name.upper())
        video_paths.append(video)
        latest = df["close"].iloc[-1]
        sma50 = df["close"].rolling(50).mean().iloc[-1]
        sma200 = df["close"].rolling(200).mean().iloc[-1]
        rsi_val = ta.rsi(df["close"], length=14).iloc[-1]
        data_summary.append((name.title(), symbol[:-4], latest, sma50, sma200, rsi_val))
    date = datetime.utcnow().strftime("%B %d, %Y")
    # Build prompt
    summary_lines = "\n".join(
        f"- {n} (${t}): Close={v:.2f}, 50D MA={s50:.2f}, 200D MA={s200:.2f}, RSI={r:.1f}"
        for n, t, v, s50, s200, r in data_summary
    )
    sections_placeholder = ""
    for (n, t, v, s50, s200, r), img, vid in zip(data_summary, img_paths, video_paths):
        sections_placeholder += f"## {n} (${t})\n"                                 f"![Chart]({img})\n"                                 f"<video controls src=\"{vid}\"></video>\n\n"
    prompt = f"""
You are Hunter the Web3 Dobie 🐾 — a seasoned crypto analyst and educator.

Write a detailed 4,000–5,000 word Substack article titled:
"Weekly Technical Analysis for Bitcoin, Ethereum, Solana, XRP, and Optimism: A Dobie's Deep Dive"

Structure the article **per token** as follows:
### {data_summary[0][0]} (${data_summary[0][1]})
- Include long-term (1+ year) trend analysis.
- Medium-term (3–6 month) momentum discussion.
- Short-term (weekly) scenario and key levels.
- Reference the chart image and the RSI animation below.

{sections_placeholder}

After covering all tokens, conclude with:
- Cross-token insights.
- Actionable tips.
- Reminder to follow @Web3_Dobie and "As always, this is NFA — Hunter 🐾".

Include the data summary below the title:
{summary_lines}

Today is {date}.
"""
    article = generate_gpt_text(prompt, max_tokens=6500)
    title_slug = slugify(f"weekly-ta-{date}")
    filename = f"{POST_DIR}/{date}_{title_slug}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(article)
    log_substack_post_to_notion(article.splitlines()[0], filename)
    return filename

if __name__ == "__main__":
    path = generate_ta_substack_article()
    print(f"✅ Generated Substack article at {path}")
