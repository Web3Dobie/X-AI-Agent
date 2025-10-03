# jobs/ta_article.py

import logging
import os
from datetime import datetime
from typing import Dict, Optional

import pandas as pd
import pandas_ta as ta
import requests
import matplotlib.pyplot as plt

from services.database_service import DatabaseService
from services.hunter_ai_service import get_hunter_ai_service
from utils.x_post import post_thread, upload_media

logger = logging.getLogger(__name__)

# Token configuration
TOKENS = {
    "bitcoin": "BTCUSDT",
    "ethereum": "ETHUSDT", 
    "solana": "SOLUSDT",
    "ripple": "XRPUSDT",
    "dogecoin": "DOGEUSDT"
}

# -----------------------------------------------------------------------------
# --- Helper Functions ---
# -----------------------------------------------------------------------------

def _fetch_ohlcv(symbol: str, limit=1000) -> pd.DataFrame:
    """Fetches OHLCV data from the Binance public API."""
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": "1d", "limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        df = pd.DataFrame(
            data,
            columns=["timestamp", "open", "high", "low", "close", "volume", 
                    "close_time", "quote_asset_volume", "trades", 
                    "taker_buy_base", "taker_buy_quote", "ignore"]
        )
        df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("date", inplace=True)
        return df[["open", "high", "low", "close", "volume"]].astype(float)
    except Exception as e:
        logger.error(f"Error fetching OHLC for {symbol}: {e}")
        return pd.DataFrame()


def _generate_chart(df: pd.DataFrame, token_name: str) -> Optional[str]:
    """Generates and saves a chart, returning the public URL."""
    try:
        out_dir = "/app/charts"
        os.makedirs(out_dir, exist_ok=True)
        
        df_year = df.loc[df.index > (df.index[-1] - pd.Timedelta(days=365))]
        
        # Create figure with three panels
        fig = plt.figure(figsize=(12, 8))
        gs = fig.add_gridspec(3, 1, height_ratios=[2, 1, 1], hspace=0.4)
        
        # Price panel with candlesticks
        ax1 = fig.add_subplot(gs[0])
        for idx, row in df_year.iterrows():
            color = 'green' if row['close'] >= row['open'] else 'red'
            ax1.bar(idx, abs(row['close'] - row['open']), 
                   bottom=min(row['open'], row['close']), 
                   width=0.8, color=color, alpha=0.6)
            ax1.plot([idx, idx], [row['low'], row['high']], 
                    color=color, linewidth=1)
        
        # Add moving averages if present
        if 'sma10' in df_year.columns:
            ax1.plot(df_year.index, df_year['sma10'], 
                    label='SMA10', color='purple', linewidth=1)
        if 'sma50' in df_year.columns:
            ax1.plot(df_year.index, df_year['sma50'], 
                    label='SMA50', color='orange', linewidth=1)
        if 'sma200' in df_year.columns:
            ax1.plot(df_year.index, df_year['sma200'], 
                    label='SMA200', color='blue', linewidth=1)
        
        ax1.set_title(f"{token_name} Price Chart - Last 365 Days")
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        plt.setp(ax1.get_xticklabels(), visible=False)
        
        # RSI panel
        ax2 = fig.add_subplot(gs[1])
        if 'rsi' in df_year.columns:
            ax2.plot(df_year.index, df_year['rsi'], color='purple', label='RSI')
            ax2.axhline(y=70, color='r', linestyle='--', alpha=0.3)
            ax2.axhline(y=30, color='g', linestyle='--', alpha=0.3)
            ax2.set_ylabel('RSI')
            ax2.grid(True, alpha=0.3)
            ax2.legend()
        plt.setp(ax2.get_xticklabels(), visible=False)
        
        # MACD panel
        ax3 = fig.add_subplot(gs[2])
        if all(x in df_year.columns for x in ['macd', 'macd_signal']):
            ax3.plot(df_year.index, df_year['macd'], 
                    color='blue', label='MACD')
            ax3.plot(df_year.index, df_year['macd_signal'], 
                    color='orange', label='Signal')
            hist = df_year['macd'] - df_year['macd_signal']
            ax3.bar(df_year.index, hist, 
                   color=['red' if x < 0 else 'green' for x in hist], 
                   alpha=0.3)
            ax3.set_ylabel('MACD')
            ax3.grid(True, alpha=0.3)
            ax3.legend()
        
        plt.xticks(rotation=45)
        fig.align_ylabels([ax1, ax2, ax3])
        
        file_name = f"{token_name.lower()}_ta_article_chart.png"
        img_path = os.path.join(out_dir, file_name)
        plt.savefig(img_path, dpi=300, bbox_inches='tight', pad_inches=0.2)
        plt.close()
        
        public_chart_url = f"https://dutchbrat.com/charts/{file_name}"
        logger.info(f"Chart for {token_name} saved: {public_chart_url}")
        return public_chart_url
        
    except Exception as e:
        logger.error(f"Failed to generate chart for {token_name}: {e}")
        return None


def _analyze_token_patterns(df: pd.DataFrame) -> Dict:
    """Analyzes token patterns from a DataFrame."""
    recent = df.loc[df.index > (df.index[-1] - pd.Timedelta(days=30))]
    window = min(5, len(recent) // 4)
    
    if window == 0:
        return {
            'trend': 'neutral',
            'pattern': 'not enough data',
            'support': 0,
            'resistance': 0,
            'volatility': 0,
            'volume': {}
        }
    
    highs = recent['high'].rolling(window=window, center=True).max()
    lows = recent['low'].rolling(window=window, center=True).min()
    
    patterns = {
        'trend': 'neutral',
        'pattern': 'trading channel',
        'support': round(lows.mean(), 2),
        'resistance': round(highs.mean(), 2),
        'volatility': round(
            (recent['high'] - recent['low']).mean() / recent['close'].mean() * 100, 
            2
        ),
        'volume': {
            'current': df['volume'].iloc[-1],
            'average': df['volume'].rolling(30).mean().iloc[-1],
            'trend': 'stable'
        }
    }
    
    return patterns


def _add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Adds technical indicators to DataFrame."""
    df["sma10"] = ta.sma(df["close"], length=10)
    df["sma50"] = ta.sma(df["close"], length=50)
    df["sma200"] = ta.sma(df["close"], length=200)
    df["rsi"] = ta.rsi(df["close"], length=14)
    
    macd = ta.macd(df["close"])
    if macd is not None and not macd.empty:
        macd_col = next((col for col in macd.columns if col.startswith('MACD_')), None)
        signal_col = next((col for col in macd.columns if col.startswith('MACDs_')), None)
        
        if macd_col and signal_col:
            df["macd"] = macd[macd_col]
            df["macd_signal"] = macd[signal_col]
    
    df.dropna(inplace=True)
    return df


# -----------------------------------------------------------------------------
# --- Main Job Function ---
# -----------------------------------------------------------------------------

def run_ta_article_job():
    """
    Generates a comprehensive weekly TA article covering multiple tokens,
    saves it locally, and posts an announcement tweet.
    """
    logger.info("Starting Weekly TA Article Job...")
    db_service = DatabaseService()
    hunter_ai = get_hunter_ai_service()
    
    try:
        date_str = datetime.utcnow().strftime("%B %d, %Y")
        article_sections = []
        token_analyses_summary = []

        # 1. Analyze each token
        for name, symbol in TOKENS.items():
            logger.info(f"Analyzing {name}...")
            
            df = _fetch_ohlcv(symbol)
            if df.empty:
                logger.warning(f"No data for {name}, skipping")
                continue

            df = _add_indicators(df)
            if df.empty:
                logger.warning(f"Insufficient data after indicators for {name}")
                continue

            chart_url = _generate_chart(df, name.title())
            patterns = _analyze_token_patterns(df)
            price = df['close'].iloc[-1]
            
            # Prepare analysis summary
            analysis_data = {
                'name': name.title(),
                'price': price,
                'chart_url': chart_url,
                'patterns': patterns,
                'indicators': {
                    'rsi': df['rsi'].iloc[-1],
                    'sma10': df['sma10'].iloc[-1],
                    'sma50': df['sma50'].iloc[-1],
                    'sma200': df['sma200'].iloc[-1]
                }
            }
            token_analyses_summary.append(analysis_data)
            
            # Generate token-specific analysis with Hunter's voice
            token_prompt = f"""
Analyze {name.title()} based on this current data:

**Price:** ${price:,.2f}
**Trend:** {patterns['trend']}
**Support/Resistance:** ${patterns['support']:,.2f} / ${patterns['resistance']:,.2f}
**RSI:** {analysis_data['indicators']['rsi']:.1f}
**Volume Trend:** {patterns['volume']['trend']}

Write a technical analysis covering:
- Current price action and trend
- Support/resistance analysis
- Indicator signals (RSI, moving averages)
- Trading outlook

Maximum 300 words. Use your witty, insightful voice.
"""
            
            token_analysis = hunter_ai.generate_analysis(token_prompt, max_tokens=500)
            
            if chart_url:
                article_sections.append(
                    f"\n## {name.title()} Analysis\n\n"
                    f"![{name.title()} Chart]({chart_url})\n\n"
                    f"{token_analysis}\n"
                )
            else:
                article_sections.append(f"\n## {name.title()} Analysis\n\n{token_analysis}\n")

        # 2. Generate cross-market analysis
        if token_analyses_summary:
            summary_lines = [
                f"- {a['name']}: ${a['price']:,.2f}, {a['patterns']['trend']} trend"
                for a in token_analyses_summary
            ]
            
            cross_market_prompt = f"""
Analyze the overall crypto market based on these current conditions:

{chr(10).join(summary_lines)}

Write a cross-market analysis covering:
- Overall market sentiment
- Correlation patterns between assets
- Volume trends across tokens
- Forward outlook for the market

Be insightful and actionable. Maximum 400 words.
"""
            
            cross_market_content = hunter_ai.generate_analysis(
                cross_market_prompt, 
                max_tokens=800
            )
            
            article_sections.append(
                "\n## Cross-Market Analysis\n\n" + cross_market_content
            )

        # 3. Assemble and save the final article
        article_title = f"Weekly Technical Analysis: {date_str}"
        
        intro = f"""
Hello Everyone! Hunter the Web3 Dobie here, your go-to crypto analyst. 
Let's dig into the technicals this week for five of the top cryptos: 
Bitcoin ($BTC), Ethereum ($ETH), Solana ($SOL), Ripple ($XRP), and Dogecoin ($DOGE).
"""
        
        footer = """
---

Follow @Web3_Dobie for more insights! This is not financial advice.

Stay curious, stay vigilant, and keep those tails wagging!
"""
        
        full_article_content = (
            f"# {article_title}\n\n"
            f"{intro}\n"
            + "\n".join(article_sections) +
            f"\n{footer}"
        )
        
        # Save to file
        date_str_filename = datetime.utcnow().strftime("%Y-%m-%d")
        file_name = f"{date_str_filename}_weekly-technical-analysis.md"
        article_path = f"/app/posts/ta/{file_name}"
        
        os.makedirs(os.path.dirname(article_path), exist_ok=True)
        with open(article_path, 'w', encoding='utf-8') as f:
            f.write(full_article_content)
        
        logger.info(f"TA Article saved to: {article_path}")

        # 4. Post announcement tweet
        public_article_url = f"https://dutchbrat.com/articles/ta/{file_name}"
        
        announcement_tweet = (
            f"Weekly Technical Analysis - {date_str}\n\n"
            f"Deep dive into $BTC, $ETH, $SOL, $XRP, and $DOGE\n\n"
            f"Charts, patterns, and insights await...\n\n"
            f"Read more:\n{public_article_url}\n\n"
            f"As always, this is NFA"
        )
        
        img_path = "/app/content/assets/hunter_poses/substack_ta.png"
        media_id = upload_media(img_path) if os.path.exists(img_path) else None
        
        post_result = post_thread(
            [announcement_tweet], 
            category='ta_article_announcement', 
            media_id_first=media_id
        )
        
        # 5. Log to database
        if post_result and post_result.get("error") is None:
            final_tweet_id = post_result.get("final_tweet_id")
            
            db_service.log_content(
                content_type="ta_article_announcement",
                tweet_id=final_tweet_id,
                details=announcement_tweet,
                headline_id=None,
                ai_provider=hunter_ai.provider.value,
                notion_url=public_article_url
            )
            
            logger.info("Successfully posted TA article announcement")
        else:
            logger.error(f"Failed to post announcement: {post_result.get('error')}")

    except Exception as e:
        logger.error(f"Failed to complete TA article job: {e}", exc_info=True)
        raise