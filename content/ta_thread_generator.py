"""
TA Thread Generator Module:
Fetches OHLC data, computes indicators, logs TA history,
and generates GPT-powered threads for weekly token analysis.
"""

import logging
import os
from datetime import datetime

import pandas as pd
import pandas_ta as ta
import requests
import matplotlib.pyplot as plt

from utils import DATA_DIR, LOG_DIR, generate_gpt_thread, post_thread, upload_media 
from utils.config import CHART_DIR

# Configure logging
log_file = os.path.join(LOG_DIR, "ta_thread_generator.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Path for TA history log
TA_LOG = os.path.join(DATA_DIR, "ta_log.csv")
os.makedirs(DATA_DIR, exist_ok=True)


def fetch_ohlc_binance(symbol="BTCUSDT", interval="1d", limit=1000) -> pd.DataFrame:
    """
    Fetches OHLC data from Binance.
    """
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(
            data,
            columns=[
                "timestamp", "open", "high", "low", "close",
                "volume", "close_time", "quote_asset_volume",
                "trades", "taker_buy_base", "taker_buy_quote", "ignore",
            ],
        )
        df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("date", inplace=True)
        return df[["open", "high", "low", "close", "volume"]].astype(float)
    except Exception as e:
        logging.error(f"Error fetching OHLC for {symbol}: {e}")
        return pd.DataFrame()


def save_token_chart(df, token, out_dir="content/charts", timeframe_days=365):
    """
    Saves a multi-panel chart with candlesticks, SMAs, RSI and MACD.
    """
    if out_dir is None:
        out_dir = CHART_DIR
    
    os.makedirs(out_dir, exist_ok=True)
    
    # Get last year of data using proper pandas filtering
    df_year = df.loc[df.index > (df.index[-1] - pd.Timedelta(days=timeframe_days))]
    
    # Create figure with better spacing
    fig = plt.figure(figsize=(12, 8))
    # Adjust GridSpec with proper spacing
    gs = fig.add_gridspec(3, 1, height_ratios=[2, 1, 1], hspace=0.4)
    
    # Price panel
    ax1 = fig.add_subplot(gs[0])
    
    # Plot candlesticks
    for idx, row in df_year.iterrows():
        color = 'green' if row['close'] >= row['open'] else 'red'
        bottom = min(row['open'], row['close'])
        height = abs(row['close'] - row['open'])
        
        # Plot body
        ax1.bar(idx, height, bottom=bottom, width=0.8, 
                color=color, alpha=0.6)
        
        # Plot wicks
        ax1.plot([idx, idx], [row['low'], row['high']], 
                 color=color, linewidth=1)

    # Add SMAs
    if 'sma10' in df_year.columns:
        ax1.plot(df_year.index, df_year['sma10'], 
                 label='SMA10', color='purple', linewidth=1)
    if 'sma50' in df_year.columns:
        ax1.plot(df_year.index, df_year['sma50'], 
                 label='SMA50', color='orange', linewidth=1)
    if 'sma200' in df_year.columns:
        ax1.plot(df_year.index, df_year['sma200'], 
                 label='SMA200', color='blue', linewidth=1)

    # Format axes before adding shared axes
    ax1.set_title(f"{token.upper()} Price Chart - Last 365 Days")
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    plt.setp(ax1.get_xticklabels(), visible=False)  # Hide x-labels for top panel

    # RSI panel with proper spacing
    ax2 = fig.add_subplot(gs[1])
    if 'rsi' in df_year.columns:
        ax2.plot(df_year.index, df_year['rsi'], color='purple', label='RSI')
        ax2.axhline(y=70, color='r', linestyle='--', alpha=0.3)
        ax2.axhline(y=30, color='g', linestyle='--', alpha=0.3)
        ax2.set_ylabel('RSI')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
    plt.setp(ax2.get_xticklabels(), visible=False)  # Hide x-labels for middle panel

    # MACD panel with proper spacing
    ax3 = fig.add_subplot(gs[2])
    if all(x in df_year.columns for x in ['macd', 'macd_signal']):
        ax3.plot(df_year.index, df_year['macd'], color='blue', label='MACD')
        ax3.plot(df_year.index, df_year['macd_signal'], color='orange', label='Signal')
        hist = df_year['macd'] - df_year['macd_signal']
        ax3.bar(df_year.index, hist, color=['red' if x < 0 else 'green' for x in hist], 
                alpha=0.3)
        ax3.set_ylabel('MACD')
        ax3.grid(True, alpha=0.3)
        ax3.legend()

    # Format x-axis on bottom panel only
    plt.xticks(rotation=45)
    
    # Adjust spacing between subplots
    fig.align_ylabels([ax1, ax2, ax3])
    
    # Save with proper bounds
    img_path = os.path.join(out_dir, f"{token.lower()}_chart.png")
    plt.savefig(img_path, dpi=300, bbox_inches='tight', pad_inches=0.2)
    plt.close()
    
    return img_path

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds SMA, RSI, MACD indicators to DataFrame.
    """
    df["sma10"] = ta.sma(df["close"], length=10)
    df["sma50"] = ta.sma(df["close"], length=50)
    df["sma200"] = ta.sma(df["close"], length=200)
    df["rsi"] = ta.rsi(df["close"], length=14)
    macd = ta.macd(df["close"])
    df["macd"] = macd["MACD_12_26_9"]
    df["macd_signal"] = macd["MACDs_12_26_9"]
    df.dropna(inplace=True)
    return df


def log_ta_entry(token: str, context: dict, summary: str):
    """
    Logs TA context and GPT summary into TA_LOG CSV.
    """
    entry = {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "token": token.upper(),
        "close": context["close"],
        "sma10": context["sma10"],  # Added SMA10
        "sma50": context["sma50"],
        "sma200": context["sma200"],
        "rsi": context["rsi"],
        "macd": context["macd"],
        "macd_signal": context["macd_signal"],
        "gpt_summary": summary.replace("\n", " "),
    }
    # Bootstrap file if missing
    try:
        df = pd.read_csv(TA_LOG)
    except FileNotFoundError:
        df = pd.DataFrame(columns=entry.keys())
    df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
    df.to_csv(TA_LOG, index=False)
    logging.info(f"Logged TA entry for {token.upper()}")


def fetch_last_ta(token: str) -> dict:
    """
    Retrieves the most recent TA entry for the given token.
    Returns empty dict if none exists.
    """
    try:
        df = pd.read_csv(TA_LOG)
    except FileNotFoundError:
        # First run, no log yet
        return {}

    # Filter by token and sort
    df = df[df["token"] == token.upper()]
    if df.empty:
        return {}
    last = df.sort_values("date").iloc[-1].to_dict()
    return last


def fetch_ohlc(token: str, days: int = 1000) -> pd.DataFrame:
    """
    Maps token to Binance symbol and fetches OHLC data.
    """
    mapping = {
        "btc": "BTCUSDT",
        "eth": "ETHUSDT",
        "sol": "SOLUSDT",
        "xrp": "XRPUSDT",
        "doge": "DOGEUSDT",
    }
    symbol = mapping.get(token.lower())
    if not symbol:
        raise ValueError(f"Unsupported token: {token}")
    return fetch_ohlc_binance(symbol, limit=days)

def analyze_chart_patterns(df: pd.DataFrame) -> dict:
    """
    Analyzes recent price action for common chart patterns.
    """
    # Get last 30 days of data for pattern analysis
    recent = df.loc[df.index > (df.index[-1] - pd.Timedelta(days=30))]  # Fixed deprecated last()
    
    # Find local highs and lows with adaptive window
    window = min(5, len(recent) // 4)  # Adaptive window size
    highs = recent['high'].rolling(window=window, center=True).max()
    lows = recent['low'].rolling(window=window, center=True).min()
    
    # Analyze trend
    patterns = {
        'trend': 'neutral',
        'pattern': 'none',
        'support': round(lows.mean(), 2),
        'resistance': round(highs.mean(), 2)
    }
    
    # Trend analysis with more granular checks
    high_changes = highs.diff()
    low_changes = lows.diff()
    
    if (high_changes > 0).sum() / len(high_changes) > 0.7:  # 70% of highs are higher
        patterns['trend'] = 'uptrend'
        patterns['pattern'] = 'higher highs and higher lows'
    elif (high_changes < 0).sum() / len(high_changes) > 0.7:  # 70% of highs are lower
        patterns['trend'] = 'downtrend'
        patterns['pattern'] = 'lower highs and lower lows'
    
    # Enhanced channel detection
    price_range = (highs.mean() - lows.mean()) / lows.mean()
    if price_range < 0.05:  # 5% range for channel
        patterns['pattern'] = 'trading channel'
    
    return patterns

def generate_ta_thread_with_memory(token: str) -> tuple[list[str], str]:
    """
    Generates a 4-part TA thread with memory of previous call.
    Returns (thread, chart_path)
    """
    df = fetch_ohlc(token)
    df = add_indicators(df)
    if df.empty:
        logging.warning(f"No data to generate TA for {token.upper()}")
        return [f"⚠️ Not enough data to analyze {token.upper()} yet."], None

    chart_path = save_token_chart(df, token)

    recent = df.iloc[-1]
    context = {
        "token":  token.upper(),
        "date":   datetime.utcnow().strftime("%b %d"),
        "close":  f"{recent['close']:,.2f}",  # Add comma formatting
        "sma10":  f"{recent['sma10']:,.2f}",  # Add comma formatting
        "sma50":  f"{recent['sma50']:,.2f}",  # Add comma formatting
        "sma200": f"{recent['sma200']:,.2f}", # Add comma formatting
        "rsi":    f"{recent['rsi']:.1f}",
        "macd":   f"{recent['macd']:.3f}",
        "macd_signal": f"{recent['macd_signal']:.3f}",
    }

    # Add chart pattern analysis
    patterns = analyze_chart_patterns(df)
    context.update({
        "trend": patterns['trend'],
        "pattern": patterns['pattern'],
        "support": patterns['support'],
        "resistance": patterns['resistance']
    })

    last = fetch_last_ta(token)
    memory = ""
    if last:
        memory = (
            f"\n\nLast week's call: Close was ${last['close']}, "
            f"RSI was {last['rsi']}, and we said: \"{last['gpt_summary'][:150]}...\""
        )
        logging.info(f"Reusing memory for {token.upper()}: {memory}")

    prompt = (
        f"You are Hunter, a crypto analyst. Create a 4-part tweet thread for "
        f"${context['token']} as of {context['date']}: close=${context['close']}, "
        f"SMA10=${context['sma10']}, SMA50=${context['sma50']}, SMA200=${context['sma200']}, "  # Add $ signs
        f"RSI={context['rsi']}, MACD={context['macd']} vs signal={context['macd_signal']}. "
        f"Chart shows {context['pattern']}, overall {context['trend']} "
        f"with support ~${context['support']:,.2f} and resistance ~${context['resistance']:,.2f}."  # Format support/resistance
        f"{memory} "
        "Each tweet <280 chars, no emojis, no hashtags. "
        "Start first tweet with 'Daily Dobie Drawings 🎨\n\n'. "
        "Focus on both indicators and visible chart patterns in your analysis. "
        "Separate tweets with '---'."
    )
    logging.info(f"Generating TA thread for {token.upper()} ({context['date']})")
    try:
        thread = generate_gpt_thread(prompt, max_parts=4, delimiter="---")
        logging.info(f"DEBUG: generate_gpt_thread() returned: {thread}")
    except Exception as e:
        logging.error(f"ERROR calling generate_gpt_thread(): {e}")
        return [f"⚠️ GPT call failed for {token.upper()}"], chart_path
    if not thread or len(thread) < 4:
        logging.error(f"Incomplete GPT thread for {token.upper()}")
        return [f"⚠️ GPT returned incomplete thread for {context['token']}"], chart_path

    else:
        # Clean up any stray sign-offs and ensure final sign-off
        for i in range(4):
            thread[i] = thread[i].replace("— Hunter", "").strip()

        # Remove any accidental "As always, this is NFA" from part 4
        thread[3] = thread[3].replace("As always, this is NFA", "").strip()

        # Append clean sign-off
        thread[3] += " What do you think? - As always, this is NFA — Hunter 🐾"

        # Log TA entry
        summary_text = " ".join(thread)
        log_ta_entry(token, context, summary_text)

        return thread, chart_path

def post_substack_announcement(substack_slug: str) -> bool:
    """
    Generates and posts a tweet announcing the latest Substack TA article.
    
    Args:
        substack_slug: The unique identifier/slug of the Substack article
    
    Returns:
        bool: True if posted successfully, False otherwise
    """
    try:
        # Generate tweet content
        date_str = datetime.now().strftime("%B %d, %Y")
        image_path = "content/assets/hunter_poses/substack_ta.png"
        
        tweet = (
            f"🎨 Weekly Technical Analysis - {date_str}\n\n"
            f"Deep dive into $BTC, $ETH, $SOL, $XRP, and $DOGE\n\n"
            f"✨ Charts, patterns, and insights await...\n\n"
            f"🔗 Read more:\n"
            f"https://web3dobie.substack.com/p/{substack_slug}\n\n"
            f"As always, this is NFA 🐾"
        )
        
        # Verify image exists
        if not os.path.exists(image_path):
            logging.error(f"Image not found: {image_path}")
            return False
            
        # Upload media and post
        media_id = upload_media(image_path)
        if not media_id:
            logging.error("Failed to upload image")
            return False
            
        result = post_thread(
            thread_parts=[tweet],
            category='substack_announcement',
            media_id_first=media_id
        )
        
        success = result.get("posted", 0) == 1
        if success:
            logging.info("✅ Successfully posted Substack announcement")
        else:
            logging.error(f"❌ Failed to post announcement: {result.get('error', 'unknown error')}")
        return success
            
    except Exception as e:
        logging.error(f"Error posting Substack announcement: {str(e)}")
        return False

# Update main execution block
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--substack":
        if len(sys.argv) < 3:
            print("Usage: python3 ta_thread_generator.py --substack <substack-slug>")
            sys.exit(1)
            
        substack_slug = sys.argv[2]
        success = post_substack_announcement(substack_slug)
        
        if success:
            print("✅ Successfully posted Substack announcement!")
        else:
            print("❌ Failed to post Substack announcement")
            sys.exit(1)
    
    else:
        # Default to BTC analysis if no valid args
        tok = sys.argv[1] if len(sys.argv) > 1 else "btc"
        tweets, chart_path = generate_ta_thread_with_memory(tok)
        for idx, txt in enumerate(tweets, 1):
            print(f"--- Tweet {idx} ---\n{txt}\n")
        print(f"Chart path for tweet 1: {chart_path}")
