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

from utils import DATA_DIR, LOG_DIR, generate_gpt_thread

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


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds SMA, RSI, MACD indicators to DataFrame.
    """
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


def generate_ta_thread_with_memory(token: str) -> list[str]:
    """
    Generates a 4-part TA thread with memory of previous call.
    """
    df = fetch_ohlc(token)
    df = add_indicators(df)
    if df.empty:
        logging.warning(f"No data to generate TA for {token.upper()}")
        return [f"⚠️ Not enough data to analyze {token.upper()} yet."]

    recent = df.iloc[-1]
    context = {
        "token":  token.upper(),
        "date":   datetime.utcnow().strftime("%b %d"),
        "close":  round(recent["close"], 2),
        "sma50":  round(recent["sma50"], 2),
        "sma200": round(recent["sma200"], 2),
        "rsi":    round(recent["rsi"], 1),
        "macd":   round(recent["macd"], 2),
        "macd_signal": round(recent["macd_signal"], 2),
    }

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
        f"SMA50={context['sma50']}, SMA200={context['sma200']}, RSI={context['rsi']}, "
        f"MACD={context['macd']} vs signal={context['macd_signal']}.{memory} "
        "Each tweet <280 chars, no emojis, no hashtags. "
        "Start first tweet with 'Daily Dobie Drawings 🎨\n\n'. "
        "End final tweet with 'As always, this is NFA — Hunter'. "
        "Separate tweets with '---'."
    )
    logging.info(f"Generating TA thread for {token.upper()} ({context['date']})")
    try:
        thread = generate_gpt_thread(prompt, max_parts=4, delimiter="---")
        logging.info(f"DEBUG: generate_gpt_thread() returned: {thread}")
    except Exception as e:
        logging.error(f"ERROR calling generate_gpt_thread(): {e}")
        return [f"⚠️ GPT call failed for {token.upper()}"]
    if not thread or len(thread) < 4:
        logging.error(f"Incomplete GPT thread for {token.upper()}")
        return [f"⚠️ GPT returned incomplete thread for {context['token']}"]

    else:
        # Clean up any stray sign-offs and ensure final sign-off
        for i in range(4):
            thread[i] = thread[i].replace("— Hunter", "").strip()

        # Remove any accidental "As always, this is NFA" from part 4
        thread[3] = thread[3].replace("As always, this is NFA", "").strip()

        # Append clean sign-off
        thread[3] += " As always, this is NFA — Hunter 🐾"

        # Log TA entry
        summary_text = " ".join(thread)
        log_ta_entry(token, context, summary_text)

        return thread


if __name__ == "__main__":
    import sys

    tok = sys.argv[1] if len(sys.argv) > 1 else "btc"
    tweets = generate_ta_thread_with_memory(tok)
    for idx, txt in enumerate(tweets, 1):
        print(f"--- Tweet {idx} ---\n{txt}\n")
