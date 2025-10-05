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
from utils.url_helpers import get_article_file_path, get_image_url, get_chart_url, get_article_web_url
from utils.notion_logger import log_article_to_notion

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

def _format_volume(vol: float) -> str:
    """Format volume for display (e.g., $1.30B, $680.30M)."""
    if vol >= 1e9:
        return f"${vol/1e9:.2f}B"
    elif vol >= 1e6:
        return f"${vol/1e6:.2f}M"
    else:
        return f"${vol/1e3:.2f}K"


def _get_price_context(df: pd.DataFrame, current_price: float) -> Dict[str, any]:
    """
    Calculate where current price sits in 3-month range.
    Returns context dict with percentile, range, and descriptive text.
    """
    try:
        # Get 3-month data (last 90 days)
        df_3m = df.tail(90)
        high_3m = df_3m['high'].max()
        low_3m = df_3m['low'].min()
        
        price_range = high_3m - low_3m
        if price_range == 0:
            return {
                'percentile': 50,
                'range_low': low_3m,
                'range_high': high_3m,
                'description': 'at current levels'
            }
        
        # Calculate percentile position
        position = (current_price - low_3m) / price_range
        percentile = int(position * 100)
        
        # Generate descriptive text
        if position <= 0.25:
            distance_from_low = ((current_price - low_3m) / low_3m) * 100
            description = f"near 3-month lows ({distance_from_low:.1f}% above low of ${low_3m:,.2f})"
        elif position >= 0.75:
            distance_from_high = ((high_3m - current_price) / high_3m) * 100
            description = f"near 3-month highs ({distance_from_high:.1f}% below high of ${high_3m:,.2f})"
        else:
            description = f"in mid-range ({percentile}th percentile of 3-month range ${low_3m:,.2f}-${high_3m:,.2f})"
        
        return {
            'percentile': percentile,
            'range_low': low_3m,
            'range_high': high_3m,
            'description': description
        }
        
    except Exception as e:
        logger.warning(f"Could not calculate price context: {e}")
        return {
            'percentile': 50,
            'range_low': current_price * 0.9,
            'range_high': current_price * 1.1,
            'description': 'at current levels'
        }


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
        # Save to /app/posts/images/ to match your volume mount
        out_dir = "/app/posts/images"
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
        
        # Use naming convention from your example: {token}_{date}_advanced.png
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        file_name = f"{token_name.lower()}_{date_str}_advanced.png"
        img_path = os.path.join(out_dir, file_name)
        plt.savefig(img_path, dpi=300, bbox_inches='tight', pad_inches=0.2)
        plt.close()
        
        # FIXED: Use get_chart_url() instead of get_image_url()
        chart_url = get_chart_url(file_name)
        logger.info(f"Chart for {token_name} saved: {chart_url}")
        return chart_url
        
    except Exception as e:
        logger.error(f"Failed to generate chart for {token_name}: {e}")
        return None


def _analyze_token_patterns(df: pd.DataFrame) -> Dict:
    """Performs analysis of chart patterns and volume."""
    recent = df.loc[df.index > (df.index[-1] - pd.Timedelta(days=30))]
    window = min(5, len(recent) // 4)
    
    if window == 0:
        return {
            'trend': 'neutral',
            'pattern': 'not enough data',
            'support': 0,
            'resistance': 0,
            'volatility': 0,
            'volume': {
                'current': df['volume'].iloc[-1],
                'average': df['volume'].rolling(30).mean().iloc[-1],
                'trend': 'stable'
            }
        }
    
    highs = recent['high'].rolling(window=window, center=True).max()
    lows = recent['low'].rolling(window=window, center=True).min()
    
    # Determine trend
    sma_short = df['close'].rolling(10).mean().iloc[-1]
    sma_long = df['close'].rolling(50).mean().iloc[-1]
    trend = 'bullish' if sma_short > sma_long else 'bearish'
    
    # Calculate volume trend
    vol_recent = df['volume'].tail(7).mean()
    vol_avg = df['volume'].rolling(30).mean().iloc[-1]
    vol_trend = 'increasing' if vol_recent > vol_avg * 1.1 else 'decreasing' if vol_recent < vol_avg * 0.9 else 'stable'
    
    patterns = {
        'trend': trend,
        'pattern': 'trading channel',
        'support': round(lows.mean(), 2),
        'resistance': round(highs.mean(), 2),
        'volatility': round(
            (recent['high'] - recent['low']).mean() / recent['close'].mean() * 100, 
            2
        ),
        'volume': {
            'current': df['volume'].iloc[-1],
            'average': vol_avg,
            'trend': vol_trend
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
            price_context = _get_price_context(df, price)
            
            # Prepare analysis summary
            analysis_data = {
                'name': name.title(),
                'price': price,
                'chart_url': chart_url,
                'patterns': patterns,
                'price_context': price_context,
                'indicators': {
                    'rsi': df['rsi'].iloc[-1],
                    'sma10': df['sma10'].iloc[-1],
                    'sma50': df['sma50'].iloc[-1],
                    'sma200': df['sma200'].iloc[-1],
                    'macd': df['macd'].iloc[-1] if 'macd' in df.columns else 0,
                    'macd_signal': df['macd_signal'].iloc[-1] if 'macd_signal' in df.columns else 0
                }
            }
            token_analyses_summary.append(analysis_data)
            
            # Generate token-specific analysis with Hunter's voice
            volume_display = _format_volume(patterns['volume']['current'])
            volume_avg_display = _format_volume(patterns['volume']['average'])
            
            token_prompt = f"""You are a crypto technical analyst. Write ONLY about the data provided below.

CURRENT LIVE DATA for {name.title()} as of {date_str}:
- Current Price: ${price:,.2f}
- Price Context: {price_context['description']}
- Trend: {patterns['trend'].title()}
- Volatility: {patterns['volatility']:.1f}%
- Support: ${patterns['support']:,.2f}
- Resistance: ${patterns['resistance']:,.2f}
- Current Volume: {volume_display}
- Average Volume: {volume_avg_display}
- Volume Trend: {patterns['volume']['trend']}
- RSI: {analysis_data['indicators']['rsi']:.1f}
- 10-day SMA: ${analysis_data['indicators']['sma10']:,.2f}
- 50-day SMA: ${analysis_data['indicators']['sma50']:,.2f}
- 200-day SMA: ${analysis_data['indicators']['sma200']:,.2f}

Write a technical analysis covering:
- Current price action and positioning in recent range
- Support/resistance analysis
- Volume interpretation
- Technical indicator signals (RSI, moving averages)
- Trading outlook

STRICT RULES:
1. ONLY use exact data provided above
2. Keep analysis factual and data-driven
3. DO NOT start with "Alright" or similar phrases
4. DO NOT end with "— Hunter 🐾" (this will be added to the article footer)
5. DO NOT use excessive emojis - keep it professional
6. Write in a direct, analytical style
7. Maximum 300 words
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

        # 2. Generate market overview (opening paragraph)
        if token_analyses_summary:
            btc_analysis = next((a for a in token_analyses_summary if a['name'] == 'Bitcoin'), None)
            
            if btc_analysis:
                overview_prompt = f"""Write a brief market overview for {date_str}.

CURRENT LIVE DATA:
- BTC Price: ${btc_analysis['price']:,.2f}
- BTC Trend: {btc_analysis['patterns']['trend']}
- BTC Volatility: {btc_analysis['patterns']['volatility']:.1f}%

Write 2-3 sentences that set the tone for the weekly technical analysis.
Focus on current market conditions based on Bitcoin's data.

RULES:
- DO NOT start with "Alright" or similar phrases
- DO NOT end with "— Hunter 🐾"
- Keep it professional and direct
- Minimal emojis
"""
                
                market_overview = hunter_ai.generate_analysis(overview_prompt, max_tokens=200)
            else:
                market_overview = f"Welcome to this week's technical analysis for {date_str}."

        # 3. Generate cross-market analysis
        if token_analyses_summary:
            summary_lines = [
                f"- {a['name']}: ${a['price']:,.2f}, {a['patterns']['trend']} trend"
                for a in token_analyses_summary
            ]
            
            bullish_count = sum(1 for a in token_analyses_summary if a['patterns']['trend'] == 'bullish')
            bearish_count = len(token_analyses_summary) - bullish_count
            volume_increasing = sum(1 for a in token_analyses_summary if a['patterns']['volume']['trend'] == 'increasing')
            
            cross_market_prompt = f"""Write a cross-market analysis using ONLY the data below from {date_str}.

CURRENT MARKET DATA:
{chr(10).join(summary_lines)}

MARKET STATISTICS:
- Bullish tokens: {bullish_count}/{len(token_analyses_summary)}
- Bearish tokens: {bearish_count}/{len(token_analyses_summary)}
- Tokens with rising volume: {volume_increasing}/{len(token_analyses_summary)}

Structure: Market Sentiment Overview, Bitcoin's Current Impact, Volume Trends, Forward Outlook

STRICT RULES:
1. ONLY use the exact prices and data listed above
2. DO NOT start with "Alright" or similar phrases
3. DO NOT end with "— Hunter 🐾" (this will be added to the article footer)
4. Use minimal emojis - keep it professional
5. Write in a direct, analytical style
6. Maximum 400 words
7. End with "Follow @Web3_Dobie for more insights"
"""
            
            cross_market_content = hunter_ai.generate_analysis(
                cross_market_prompt, 
                max_tokens=800
            )
            
            article_sections.append(
                "\n## Cross-Market Analysis\n\n" + cross_market_content
            )

        # 4. Assemble and save the final article
        article_title = f"Weekly Technical Analysis: {date_str}"
        
        # Add Hunter image at top
        hunter_image_url = get_image_url("hunter_headshot.png")
        
        footer = """
---

*Follow [@Web3_Dobie](https://twitter.com/Web3_Dobie) for more crypto insights and subscribe for weekly deep dives!*

*This is not financial advice. Always do your own research.*

Until next week,
Hunter the Web3 Dobie
"""
        
        full_article_content = (
            f"![Hunter the Dobie]({hunter_image_url})\n\n"
            f"# {article_title}\n\n"
            f"{market_overview}\n\n"
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

        # 5. Get the article file path for Notion
        article_file_path = get_article_file_path("ta", file_name)
        
        # 6. Log to Notion to get page ID
        notion_page_id = log_article_to_notion(
            headline=article_title,
            file_url=article_file_path,
            tags=["TA", "crypto", "weekly"],
            category="Technical Analysis",
            summary="A detailed review of this week's crypto market structure, volume, key levels, and forward outlook."
        )
        
        # 7. Construct public web URL for the tweet
        public_article_url = get_article_web_url(notion_page_id) if notion_page_id else article_file_path
        logger.info(f"Public article URL: {public_article_url}")
        
        # 8. Post announcement tweet
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
        
        # 9. Log to database
        if post_result and post_result.get("error") is None:
            final_tweet_id = post_result.get("final_tweet_id")
            
            db_service.log_content(
                content_type="ta_article_announcement",
                tweet_id=final_tweet_id,
                details=announcement_tweet,
                headline_id=None,
                ai_provider=hunter_ai.provider.value,
                notion_url=article_file_path
            )
            
            logger.info("Successfully posted TA article announcement")
        else:
            logger.error(f"Failed to post announcement: {post_result.get('error')}")

    except Exception as e:
        logger.error(f"Failed to complete TA article job: {e}", exc_info=True)
        raise