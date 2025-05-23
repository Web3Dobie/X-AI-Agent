
import pandas as pd
import pandas_ta as ta
import requests
import os
from datetime import datetime
from utils.gpt import generate_gpt_thread

log_path = r"D:\X AI Agent\TA History\ta_log.csv"
os.makedirs(os.path.dirname(log_path), exist_ok=True)

def fetch_ohlc_binance(symbol="BTCUSDT", interval="1d", limit=1000):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "num_trades",
            "taker_buy_base", "taker_buy_quote", "ignore"
        ])
        df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("date", inplace=True)
        df = df[["open", "high", "low", "close", "volume"]].astype(float)
        return df
    except Exception as e:
        print(f"❌ Error fetching Binance OHLC data: {e}")
        return pd.DataFrame()

def add_indicators(df):
    df["sma50"] = ta.sma(df["close"], length=50)
    df["sma200"] = ta.sma(df["close"], length=200)
    df["rsi"] = ta.rsi(df["close"], length=14)
    macd = ta.macd(df["close"])
    df["macd"] = macd["MACD_12_26_9"]
    df["macd_signal"] = macd["MACDs_12_26_9"]
    df.dropna(inplace=True)
    return df

def log_ta_entry(token, close, sma50, sma200, rsi, macd, macd_signal, gpt_summary):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    new_entry = {
        "date": today,
        "token": token.upper(),
        "close": close,
        "sma50": sma50,
        "sma200": sma200,
        "rsi": rsi,
        "macd": macd,
        "macd_signal": macd_signal,
        "gpt_summary": gpt_summary
    }
    try:
        df = pd.read_csv(log_path)
    except FileNotFoundError:
        df = pd.DataFrame(columns=new_entry.keys())
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    df.to_csv(log_path, index=False)

def fetch_last_ta(token):
    try:
        df = pd.read_csv(log_path)
    except FileNotFoundError:
        return None
    token_entries = df[df["token"] == token.upper()]
    if token_entries.empty:
        return None
    return token_entries.sort_values("date").iloc[-1].to_dict()

def fetch_ohlc(token, days=1000):
    symbol_map = {
        "btc": "BTCUSDT",
        "eth": "ETHUSDT",
        "sol": "SOLUSDT",
        "xrp": "XRPUSDT",
        "op": "OPUSDT"
    }
    symbol = symbol_map.get(token.lower())
    if not symbol:
        raise ValueError(f"Unsupported token: {token}")
    return fetch_ohlc_binance(symbol, limit=days)

def generate_ta_thread_with_memory(token: str):
    df = fetch_ohlc(token)
    df = add_indicators(df)
    if df.empty:
        return ["⚠️ Not enough data to analyze this token yet."]

    recent = df.tail(1).iloc[0]
    context = {
        "token": token.upper(),
        "date": datetime.utcnow().strftime("%b %d"),
        "close": round(recent["close"], 2),
        "sma50": round(recent["sma50"], 2),
        "sma200": round(recent["sma200"], 2),
        "rsi": round(recent["rsi"], 1),
        "macd": round(recent["macd"], 2),
        "macd_signal": round(recent["macd_signal"], 2),
    }

    last_ta = fetch_last_ta(token)
    memory_snippet = ""
    if last_ta:
        memory_snippet = (
            f"\n\nLast week's call: Close was ${last_ta['close']}, "
            f"RSI was {last_ta['rsi']}, and we said: \"{last_ta['gpt_summary'][:150]}...\""
        )

    prompt = f"""
You are Hunter the Web3 Dobie, a savvy crypto analyst with a dry sense of humor.

Create a 4-part tweet thread for ${context['token']} using this data:

- Today's close: {context['close']}
- 50-day MA: {context['sma50']}
- 200-day MA: {context['sma200']}
- RSI: {context['rsi']}
- MACD: {context['macd']} vs Signal: {context['macd_signal']}
- Date: {context['date']}{memory_snippet}

Each tweet should be clever and fact-based, in the first person. No emoji. Do not use asterisks or hashtags.

Start Tweet 1 with this header:
Daily Dobie Drawings ✍️
${context['token']} Technical Outlook [{context['date']}]

Add a line break, then your commentary. Do not repeat this header in later tweets.

End only the final tweet with:
As always, this is NFA — Hunter 🐾
"""

    thread = generate_gpt_thread(prompt, max_parts=4, delimiter="---")

    if not thread or len(thread) < 4:
        return ["⚠️ GPT returned an incomplete thread."]

    for i in range(4):
        thread[i] = thread[i].replace("— Hunter 🐾", "").strip()
        thread[i] = thread[i].replace("As always, this is NFA", "").strip()
    thread[3] += "\nAs always, this is NFA — Hunter 🐾"

    full_thread_text = "\n---\n".join(thread)

    log_ta_entry
    token=context["token"],
    close=context["close"],
    sma50=context["sma50"],
    sma200=context["sma200"],
    rsi=context["rsi"],
    macd=context["macd"],
    macd_signal=context["macd_signal"],
    gpt_summary=full_thread_text

    return thread

if __name__ == "__main__":
    import sys
    token = sys.argv[1] if len(sys.argv) > 1 else "btc"
    print(f"🔍 Generating TA thread for ${token.upper()}...\n")
    thread = generate_ta_thread_with_memory(token)
    if thread:
        for i, part in enumerate(thread, 1):
            print(f"\n--- Tweet {i} ---\n{part}")
    else:
        print("⚠️ No thread generated.")
