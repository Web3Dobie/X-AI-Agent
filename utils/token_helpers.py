# utils/token_helpers.py

import os
from datetime import datetime
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt

from utils.blob import upload_to_blob  # Assuming this already exists

CHART_DIR = os.getenv("CHART_DIR", "./charts")
os.makedirs(CHART_DIR, exist_ok=True)

def fetch_ohlcv(symbol: str, limit: int = 365) -> pd.DataFrame:
    import requests
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": "1d", "limit": limit}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = pd.DataFrame(
        resp.json(),
        columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "qav", "num_trades", "taker_base",
            "taker_quote", "ignore",
        ],
    )
    data["date"] = pd.to_datetime(data["open_time"], unit="ms")
    data.set_index("date", inplace=True)
    return data[["open", "high", "low", "close", "volume"]].astype(float)

def analyze_token_patterns(df: pd.DataFrame) -> dict:
    df['sma50'] = df['close'].rolling(50).mean()
    df['sma200'] = df['close'].rolling(200).mean()
    latest = df.iloc[-1]
    trend = "bullish" if latest['close'] > latest['open'] else "bearish"
    support = df['low'].rolling(window=20).min().iloc[-1]
    resistance = df['high'].rolling(window=20).max().iloc[-1]
    current_volume = df['volume'].iloc[-1] * df['close'].iloc[-1]
    rolling_volume = df['volume'].rolling(window=20).mean() * df['close']
    avg_volume = rolling_volume.iloc[-1]
    volume_trend = "increasing" if current_volume > avg_volume else "decreasing"
    volume_change = ((current_volume - avg_volume) / avg_volume) * 100
    price_momentum = df['close'].pct_change(5).iloc[-1] * 100
    returns = df['close'].pct_change().dropna()
    volatility = returns.std() * 100
    golden_cross = (
        df['sma50'].iloc[-1] > df['sma200'].iloc[-1] and
        df['sma50'].iloc[-2] <= df['sma200'].iloc[-2]
    )
    death_cross = (
        df['sma50'].iloc[-1] < df['sma200'].iloc[-1] and
        df['sma50'].iloc[-2] >= df['sma200'].iloc[-2]
    )
    return {
        'trend': trend,
        'support': support,
        'resistance': resistance,
        'volatility': volatility,
        'golden_cross': golden_cross,
        'death_cross': death_cross,
        'volume': {
            'current': current_volume,
            'average': avg_volume,
            'trend': volume_trend,
            'change': volume_change
        },
        'momentum': price_momentum
    }

def generate_chart(df: pd.DataFrame, token_label: str, style: str = 'advanced') -> str:
    df['sma10'] = df['close'].rolling(10).mean()
    df['sma50'] = df['close'].rolling(50).mean()
    df['sma200'] = df['close'].rolling(200).mean()
    df['rsi'] = ta.rsi(df['close'], length=14)
    macd_out = ta.macd(df['close'])
    df['macd'] = macd_out['MACD_12_26_9']
    df['macd_signal'] = macd_out['MACDs_12_26_9']

    if style == 'advanced':
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), height_ratios=[3, 1, 1])
        width = 0.6
        width2 = 0.05
        up = df[df.close >= df.open]
        down = df[df.close < df.open]
        ax1.bar(up.index, up.close-up.open, width, bottom=up.open, color='g', alpha=0.6)
        ax1.bar(up.index, up.high-up.close, width2, bottom=up.close, color='g')
        ax1.bar(up.index, up.low-up.open, width2, bottom=up.open, color='g')
        ax1.bar(down.index, down.close-down.open, width, bottom=down.open, color='r', alpha=0.6)
        ax1.bar(down.index, down.high-down.open, width2, bottom=down.open, color='r')
        ax1.bar(down.index, down.low-down.close, width2, bottom=down.close, color='r')
        ax1.plot(df.index, df['sma10'], '--', label='SMA10', color='blue', alpha=0.7)
        ax1.plot(df.index, df['sma50'], '--', label='SMA50', color='orange', alpha=0.7)
        ax1.plot(df.index, df['sma200'], '--', label='SMA200', color='red', alpha=0.7)
        ax1.set_title(f"{token_label} Technical Analysis")
        ax1.legend(loc='upper left')
        ax2.plot(df.index, df['rsi'], color='purple', alpha=0.7)
        ax2.axhline(y=70, color='r', linestyle='--', alpha=0.3)
        ax2.axhline(y=30, color='g', linestyle='--', alpha=0.3)
        ax2.set_ylabel('RSI')
        ax3.plot(df.index, df['macd'], label='MACD', color='blue', alpha=0.7)
        ax3.plot(df.index, df['macd_signal'], label='Signal', color='orange', alpha=0.7)
        ax3.set_ylabel('MACD')
        ax3.legend(loc='upper left')
    else:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(df.index, df['close'], label='Price', color='black', alpha=0.7)
        ax.plot(df.index, df['sma10'], '--', label='SMA10', color='blue', alpha=0.7)
        ax.plot(df.index, df['sma50'], '--', label='SMA50', color='orange', alpha=0.7)
        ax.plot(df.index, df['sma200'], '--', label='SMA200', color='red', alpha=0.7)
        ax.set_title(f"{token_label} Price Movement")
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # Versioned filename per run
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{token_label.lower()}_{date_str}_{style}.png"
    local_path = os.path.join(CHART_DIR, filename)
    plt.savefig(local_path, dpi=300, bbox_inches='tight')
    plt.close()

    # Upload to Azure Blob Storage
    blob_url = upload_to_blob(local_path, blob_name=filename, content_type="image/png")
    return blob_url  # Use this in your markdown/html

def generate_risk_assessment(analysis: dict) -> str:
    """Generate risk assessment based on technical indicators."""
    rsi = analysis['indicators']['rsi']
    price = analysis['price']
    support = analysis['patterns']['support']
    resistance = analysis['patterns']['resistance']
    
    risk_level = "high" if (
        rsi > 70 or rsi < 30 or
        abs((price - support) / price) < 0.05 or
        abs((resistance - price) / price) < 0.05
    ) else "moderate"
    
    return f"""### Risk Assessment
Current risk profile: {risk_level.upper()}
- RSI conditions: {'Overbought' if rsi > 70 else 'Oversold' if rsi < 30 else 'Neutral'}
- Price near {'support' if price - support < resistance - price else 'resistance'}
- Volume: {analysis['patterns']['volume']['trend']}

{'⚠️ Exercise caution - price near critical level' if risk_level == "high" else '🔍 Monitor key levels for potential entries/exits'}"""