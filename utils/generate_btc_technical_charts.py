"""
Refactored Bitcoin technical chart generator.
Writes output PNGs into CHART_DIR by default, supports custom output_dir.
"""

import os

import matplotlib.pyplot as plt
import pandas as pd
import pandas_ta as ta
import requests

from .config import CHART_DIR


def fetch_binance_ohlcv(symbol="BTCUSDT", interval="1d", limit=200):
    """
    Fetches OHLCV data from Binance for the given symbol.
    Returns a DataFrame with datetime index and float columns.
    """
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    df = pd.DataFrame(
        data,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "number_of_trades",
            "taker_buy_base_asset_volume",
            "taker_buy_quote_asset_volume",
            "ignore",
        ],
    )
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("date", inplace=True)
    df = df[["open", "high", "low", "close", "volume"]].astype(float)
    return df


def main(output_dir=None):
    """
    Generate two technical analysis charts for BTC:
      1) Price with SMA50 & SMA200
      2) RSI (14) and MACD(12,26,9)
    Saves them as PNGs in output_dir (defaults to CHART_DIR).
    """
    output_dir = output_dir or CHART_DIR
    os.makedirs(output_dir, exist_ok=True)

    # Fetch data
    df = fetch_binance_ohlcv()

    # Calculate moving averages
    df["sma50"] = df["close"].rolling(window=50).mean()
    df["sma200"] = df["close"].rolling(window=200).mean()

    # Chart 1: Price & MAs
    plt.figure(figsize=(12, 6))
    plt.plot(df["close"], label="BTC Close", linewidth=1.5)
    plt.plot(df["sma50"], label="50-day MA", linestyle="--")
    plt.plot(df["sma200"], label="200-day MA", linestyle=":")
    plt.title("Bitcoin Price & Moving Averages")
    plt.xlabel("Date")
    plt.ylabel("Price (USDT)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    trend_path = os.path.join(output_dir, "weekly_trend_channel.png")
    plt.savefig(trend_path)
    plt.close()

    # Calculate RSI and MACD
    df["rsi"] = ta.rsi(df["close"], length=14)
    macd = ta.macd(df["close"])
    df["macd"] = macd["MACD_12_26_9"]
    df["macd_signal"] = macd["MACDs_12_26_9"]

    # Chart 2: RSI & MACD
    fig, axs = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    axs[0].plot(df["rsi"], label="RSI", linewidth=1.5)
    axs[0].axhline(70, linestyle="--", linewidth=1)
    axs[0].axhline(30, linestyle="--", linewidth=1)
    axs[0].set_title("Relative Strength Index (14D)")
    axs[0].legend()
    axs[0].grid(True)

    axs[1].plot(df["macd"], label="MACD", linewidth=1.5)
    axs[1].plot(df["macd_signal"], label="Signal Line", linestyle="--")
    axs[1].set_title("MACD vs Signal")
    axs[1].legend()
    axs[1].grid(True)

    plt.tight_layout()
    rsi_macd_path = os.path.join(output_dir, "daily_rsi_macd.png")
    plt.savefig(rsi_macd_path)
    plt.close()

    print(
        f"[OK] Charts saved to {output_dir}: weekly_trend_channel.png, daily_rsi_macd.png"
    )


if __name__ == "__main__":
    main()
