# jobs/ta_thread_job.py

import logging
import os
from datetime import datetime
import pandas as pd
import pandas_ta as ta
import requests
import matplotlib.pyplot as plt

from services.database_service import DatabaseService
from services.ai_service import get_ai_service
from utils.x_post import post_thread, upload_media

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# --- Helper Functions (migrated from ta_thread_generator.py) ---
# -----------------------------------------------------------------------------

def _fetch_ohlc_binance(symbol="BTCUSDT", interval="1d", limit=1000) -> pd.DataFrame:
    """Fetches OHLCV data from the Binance public API."""
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume", "close_time", "quote_asset_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"])
        df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("date", inplace=True)
        return df[["open", "high", "low", "close", "volume"]].astype(float)
    except Exception as e:
        logger.error(f"Error fetching OHLC for {symbol} from Binance: {e}")
        return pd.DataFrame()

def _save_token_chart(df: pd.DataFrame, token: str, timeframe_days=365) -> str:
    """Generates and saves a multi-panel chart image."""
    out_dir = "/app/charts" # Using absolute path inside the container
    os.makedirs(out_dir, exist_ok=True)
    df_year = df.loc[df.index > (df.index[-1] - pd.Timedelta(days=timeframe_days))]
    
    # --- Charting logic from your original file ---
    fig = plt.figure(figsize=(12, 8))
    gs = fig.add_gridspec(3, 1, height_ratios=[2, 1, 1], hspace=0.4)
    ax1 = fig.add_subplot(gs[0])
    for idx, row in df_year.iterrows():
        color = 'green' if row['close'] >= row['open'] else 'red'
        ax1.bar(idx, abs(row['close'] - row['open']), bottom=min(row['open'], row['close']), width=0.8, color=color, alpha=0.6)
        ax1.plot([idx, idx], [row['low'], row['high']], color=color, linewidth=1)
    if 'sma10' in df_year.columns: ax1.plot(df_year.index, df_year['sma10'], label='SMA10', color='purple', linewidth=1)
    if 'sma50' in df_year.columns: ax1.plot(df_year.index, df_year['sma50'], label='SMA50', color='orange', linewidth=1)
    if 'sma200' in df_year.columns: ax1.plot(df_year.index, df_year['sma200'], label='SMA200', color='blue', linewidth=1)
    ax1.set_title(f"{token.upper()} Price Chart - Last 365 Days")
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    plt.setp(ax1.get_xticklabels(), visible=False)
    ax2 = fig.add_subplot(gs[1])
    if 'rsi' in df_year.columns:
        ax2.plot(df_year.index, df_year['rsi'], color='purple', label='RSI')
        ax2.axhline(y=70, color='r', linestyle='--', alpha=0.3)
        ax2.axhline(y=30, color='g', linestyle='--', alpha=0.3)
        ax2.set_ylabel('RSI')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
    plt.setp(ax2.get_xticklabels(), visible=False)
    ax3 = fig.add_subplot(gs[2])
    if all(x in df_year.columns for x in ['macd', 'macd_signal']):
        ax3.plot(df_year.index, df_year['macd'], color='blue', label='MACD')
        ax3.plot(df_year.index, df_year['macd_signal'], color='orange', label='Signal')
        hist = df_year['macd'] - df_year['macd_signal']
        ax3.bar(df_year.index, hist, color=['red' if x < 0 else 'green' for x in hist], alpha=0.3)
        ax3.set_ylabel('MACD')
        ax3.grid(True, alpha=0.3)
        ax3.legend()
    plt.xticks(rotation=45)
    fig.align_ylabels([ax1, ax2, ax3])
    img_path = os.path.join(out_dir, f"{token.lower()}_chart.png")
    plt.savefig(img_path, dpi=300, bbox_inches='tight', pad_inches=0.2)
    plt.close()
    logger.info(f"Chart saved to {img_path}")
    return img_path


def _add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates and adds TA indicators to the DataFrame."""
    df["sma10"] = ta.sma(df["close"], length=10)
    df["sma50"] = ta.sma(df["close"], length=50)
    df["sma200"] = ta.sma(df["close"], length=200)
    df["rsi"] = ta.rsi(df["close"], length=14)
    
    # Calculate MACD
    macd = ta.macd(df["close"])
    
    if macd is not None and not macd.empty:
        # Robustly find the correct column names instead of guessing
        macd_col = next((col for col in macd.columns if col.startswith('MACD_')), None)
        signal_col = next((col for col in macd.columns if col.startswith('MACDs_')), None)
        
        if macd_col and signal_col:
            df["macd"] = macd[macd_col]
            df["macd_signal"] = macd[signal_col]
        else:
            logger.warning("Could not find expected MACD columns in pandas_ta result.")

    df.dropna(inplace=True)
    return df

def _analyze_chart_patterns(df: pd.DataFrame) -> dict:
    """Performs a simple analysis of chart patterns."""
    recent = df.loc[df.index > (df.index[-1] - pd.Timedelta(days=30))]
    window = min(5, len(recent) // 4)
    if window == 0: return {'trend': 'neutral', 'pattern': 'not enough data', 'support': 0, 'resistance': 0}
    highs = recent['high'].rolling(window=window, center=True).max()
    lows = recent['low'].rolling(window=window, center=True).min()
    patterns = {'trend': 'neutral', 'pattern': 'none', 'support': round(lows.mean(), 2), 'resistance': round(highs.mean(), 2)}
    # (Your pattern analysis logic from the original file)
    return patterns

# -----------------------------------------------------------------------------
# --- Main Job Function (Refactored) ---
# -----------------------------------------------------------------------------

def run_ta_thread_job(token: str):
    """
    Fetches data, generates a TA thread with memory from the DB, posts it,
    and logs the new analysis back to the DB.
    """
    logger.info(f"🎨 Starting TA Thread Job for ${token.upper()}...")
    db_service = DatabaseService()
    ai_service = get_ai_service()

    try:
        # 1. Fetch live data and calculate indicators
        symbol_map = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT", "XRP": "XRPUSDT", "DOGE": "DOGEUSDT"}
        df = _fetch_ohlc_binance(symbol_map.get(token.upper()))
        if df.empty:
            logger.warning(f"No OHLC data fetched for {token}. Skipping job.")
            return
        df = _add_indicators(df)
        if df.empty:
            logger.warning(f"Not enough data to calculate indicators for {token}. Skipping job.")
            return
        
        # 2. Fetch "memory" FROM THE DATABASE, replacing the CSV read
        last_analysis = db_service.get_latest_ta_for_token(token)

        # 3. Generate prompt with new data and memory
        chart_path = _save_token_chart(df, token)
        recent = df.iloc[-1]
        patterns = _analyze_chart_patterns(df)
        context = { "token": token.upper(), "date": datetime.utcnow().strftime("%b %d"), "close": recent['close'], "sma10": recent['sma10'], "sma50": recent['sma50'], "sma200": recent['sma200'], "rsi": recent['rsi'], "macd": recent['macd'], "macd_signal": recent['macd_signal'] }

        memory_text = ""
        # ADDED: Check that last_analysis is not None AND is a dictionary
        if last_analysis and isinstance(last_analysis, dict):
            # Safely get the summary. Default to an empty string if the key is missing.
            summary = last_analysis.get('ai_summary', '')
            
            # Start building the memory text using .get() for all keys for maximum safety
            base_memory = f"\n- **Last Analysis:** Close was ${last_analysis.get('close', 0):.2f}, RSI was ${last_analysis.get('rsi', 0):.1f}"
            
            # Only add the summary part if it's not empty
            if summary:
                memory_text = base_memory + f', and we said: \"{summary[:150]}...\"'
            else:
                memory_text = base_memory + "." # End the sentence cleanly if no summary exists

        input_data = f"""
**DATA FOR {context['date']}:**
- **Token:** ${context['token']}
- **Current Price:** ${context['close']:,.2f}
- **Trend:** {patterns['trend']}
- **Chart Pattern:** {patterns['pattern']}
- **Support:** ~${patterns['support']:,.2f}
- **Resistance:** ~${patterns['resistance']:,.2f}
- **SMAs (10/50/200):** ${context['sma10']:,.2f} / ${context['sma50']:,.2f} / ${context['sma200']:,.2f}
- **RSI:** {context['rsi']:.1f}{memory_text}
"""
        task_rules = """
**TASK:** Write a 4-part tweet thread interpreting the technical data provided. Build a narrative that connects the indicators, patterns, and last week's analysis.
**RULES:**
- Each tweet must be under 280 characters.
- Start the first tweet with 'Daily Dobie Drawings 🎨\\n\\n'.
- End the final tweet with 'What do you think? - As always, this is NFA — Hunter 🐾'.
- Separate each tweet with '---'.
"""

        # 4. Generate thread with AI
        thread_parts = ai_service.generate_thread(prompt=input_data, system_instruction=task_rules, parts=4, max_tokens=2500)
        if not thread_parts or len(thread_parts) < 4:
            logger.warning(f"AI returned insufficient parts for TA thread for {token}. Skipping.")
            return
        
        # 5. Post the thread
        media_id = upload_media(chart_path) if chart_path and os.path.exists(chart_path) else None
        post_result = post_thread(thread_parts, category=f"ta_thread_{token.lower()}", media_id_first=media_id)

        # 6. Log results TO THE DATABASE
        if post_result and post_result.get("error") is None:
            logger.info(f"✅ TA thread for ${token.upper()} posted successfully.")
            final_tweet_id = post_result.get("final_tweet_id")
            full_thread_text = "\n---\n".join(thread_parts)
    
            db_service.log_content(
                content_type=f"ta_thread_{token.lower()}", 
                tweet_id=final_tweet_id,
                details=full_thread_text, 
                headline_id=None, 
                ai_provider=ai_service.provider.value
            )
    
            # Store TA data for next run's "memory"
            ta_entry_data = {
                'token': token.upper(),
                'date': datetime.utcnow().date().isoformat(),
                'close_price': float(context['close']),
                'sma_10': float(context['sma10']),
                'sma_50': float(context['sma50']),
                'sma_200': float(context['sma200']),
                'rsi': float(context['rsi']),
                'macd': float(context['macd']),
                'macd_signal': float(context['macd_signal']),
                'ai_summary': full_thread_text[:500],  # Store first 500 chars as summary
                'ai_provider': ai_service.provider.value
            }
            db_service.batch_upsert_ta_data(ta_entry_data)
        else:
            logger.error(f"Failed to post TA thread for {token}. Error: {post_result.get('error')}")

    except Exception as e:
        logger.error(f"❌ Failed to complete TA thread job for {token}: {e}", exc_info=True)
        raise