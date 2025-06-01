import matplotlib.pyplot as plt
import pandas as pd
import pandas_ta as ta
import requests


def fetch_binance_ohlcv(symbol="BTCUSDT", interval="1d", limit=200):
    """
    Fetches OHLCV data from Binance for the given symbol.
    Returns a DataFrame with datetime index and float columns.
    """
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url)
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


def main():
    # Fetch data
    btc_df = fetch_binance_ohlcv()

    # Calculate moving averages
    btc_df["sma50"] = btc_df["close"].rolling(window=50).mean()
    btc_df["sma200"] = btc_df["close"].rolling(window=200).mean()

    # Chart 1: Price and Moving Averages
    plt.figure(figsize=(12, 6))
    plt.plot(btc_df["close"], label="BTC Close", linewidth=1.5)
    plt.plot(btc_df["sma50"], label="50-day MA", linestyle="--")
    plt.plot(btc_df["sma200"], label="200-day MA", linestyle=":")
    plt.title("Bitcoin Price & Moving Averages")
    plt.xlabel("Date")
    plt.ylabel("Price (USDT)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("weekly_trend_channel.png")
    plt.close()

    # Calculate RSI and MACD
    btc_df["rsi"] = ta.rsi(btc_df["close"], length=14)
    macd = ta.macd(btc_df["close"])
    btc_df["macd"] = macd["MACD_12_26_9"]
    btc_df["macd_signal"] = macd["MACDs_12_26_9"]

    # Chart 2: RSI and MACD
    fig, axs = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    axs[0].plot(btc_df["rsi"], label="RSI", linewidth=1.5)
    axs[0].axhline(70, color="red", linestyle="--", linewidth=1)
    axs[0].axhline(30, color="green", linestyle="--", linewidth=1)
    axs[0].set_title("Relative Strength Index (14D)")
    axs[0].legend()
    axs[0].grid(True)

    axs[1].plot(btc_df["macd"], label="MACD", linewidth=1.5)
    axs[1].plot(btc_df["macd_signal"], label="Signal Line", linestyle="--", linewidth=1)
    axs[1].set_title("MACD vs Signal")
    axs[1].legend()
    axs[1].grid(True)

    plt.tight_layout()
    plt.savefig("daily_rsi_macd.png")
    plt.close()

    print("✅ Charts saved as 'weekly_trend_channel.png' and 'daily_rsi_macd.png'")


if __name__ == "__main__":
    main()
