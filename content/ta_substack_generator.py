"""
Generate detailed technical analysis articles for Substack with advanced charting.
"""

# 1. Imports and Configuration (keep existing)
import logging
import os
import re
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pandas_ta as ta
import requests

from utils import (TA_POST_DIR, generate_gpt_text, log_substack_post_to_notion)

# Configure logging
log_file = os.path.join(TA_POST_DIR, "ta_substack_generator.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def slugify(text: str) -> str:
    return re.sub(r"\W+", "-", text.lower()).strip("-")


# Token‐market symbols mapping
TOKENS = {
    "bitcoin": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "solana": "SOLUSDT",
    "ripple": "XRPUSDT",
    "dogecoin": "DOGEUSDT",
}

# Define directories
CHART_DIR = os.path.join(TA_POST_DIR, "charts")
os.makedirs(CHART_DIR, exist_ok=True)
os.makedirs(TA_POST_DIR, exist_ok=True)

# 2. Helper Functions
def fetch_ohlcv(symbol: str, limit: int = 365) -> pd.DataFrame:
    """Fetch OHLCV data from Binance API."""
    logging.info(f"Fetching data for {symbol}...")
    try:
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
        logging.info(f"Successfully fetched {len(data)} days of data for {symbol}")
        return data[["open", "high", "low", "close", "volume"]].astype(float)
    except Exception as e:
        logging.error(f"Error fetching data for {symbol}: {str(e)}")
        raise

def analyze_token_patterns(df: pd.DataFrame) -> dict:
    """
    Analyze price patterns and volatility.
    Returns a dict with trend, support, resistance, volatility and crossover patterns.
    """
    # Calculate moving averages first
    df['sma50'] = df['close'].rolling(50).mean()
    df['sma200'] = df['close'].rolling(200).mean()

    latest = df.iloc[-1]
    trend = "bullish" if latest['close'] > latest['open'] else "bearish"
    
    # Calculate support and resistance
    support = df['low'].rolling(window=20).min().iloc[-1]
    resistance = df['high'].rolling(window=20).max().iloc[-1]

    # Calculate USDT volume (daily volume in quote currency)
    current_volume = df['volume'].iloc[-1] * df['close'].iloc[-1]  # Convert to USDT value
    rolling_volume = df['volume'].rolling(window=20).mean() * df['close']  # Volume in USDT
    avg_volume = rolling_volume.iloc[-1]
    
    volume_trend = "increasing" if current_volume > avg_volume else "decreasing"
    volume_change = ((current_volume - avg_volume) / avg_volume) * 100
    
    # Price momentum and volatility
    price_momentum = df['close'].pct_change(5).iloc[-1] * 100  # 5-day momentum
    returns = df['close'].pct_change().dropna()
    volatility = returns.std() * 100  # in percentage
    
    # Detect golden/death cross
    golden_cross = df['sma50'].iloc[-1] > df['sma200'].iloc[-1] and df['sma50'].iloc[-2] <= df['sma200'].iloc[-2]
    death_cross = df['sma50'].iloc[-1] < df['sma200'].iloc[-1] and df['sma50'].iloc[-2] >= df['sma200'].iloc[-2]

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

# 3. Chart Generation (combined version)
def generate_chart(df: pd.DataFrame, token_label: str, style: str = 'advanced') -> str:
    """
    Generate chart with indicators. Style can be 'advanced' or 'simple'.
    Returns path to saved chart.
    """

    
    # Calculate indicators once
    df['sma10'] = df['close'].rolling(10).mean()
    df['sma50'] = df['close'].rolling(50).mean()
    df['sma200'] = df['close'].rolling(200).mean()
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['macd'] = ta.macd(df['close'])['MACD_12_26_9']
    df['macd_signal'] = ta.macd(df['close'])['MACDs_12_26_9']

    if style == 'advanced':
        # Create figure with secondary y axis
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), height_ratios=[3, 1, 1])
        
        # Plot candlesticks
        width = 0.6
        width2 = 0.05
        up = df[df.close >= df.open]
        down = df[df.close < df.open]
        
        # Plot up candles
        ax1.bar(up.index, up.close-up.open, width, bottom=up.open, color='g', alpha=0.6)
        ax1.bar(up.index, up.high-up.close, width2, bottom=up.close, color='g')
        ax1.bar(up.index, up.low-up.open, width2, bottom=up.open, color='g')
        
        # Plot down candles
        ax1.bar(down.index, down.close-down.open, width, bottom=down.open, color='r', alpha=0.6)
        ax1.bar(down.index, down.high-down.open, width2, bottom=down.open, color='r')
        ax1.bar(down.index, down.low-down.close, width2, bottom=down.close, color='r')

        # Add moving averages to main chart
        ax1.plot(df.index, df['sma10'], '--', label='SMA10', color='blue', alpha=0.7)
        ax1.plot(df.index, df['sma50'], '--', label='SMA50', color='orange', alpha=0.7)
        ax1.plot(df.index, df['sma200'], '--', label='SMA200', color='red', alpha=0.7)
        
        # Add RSI subplot
        ax2.plot(df.index, df['rsi'], color='purple', alpha=0.7)
        ax2.axhline(y=70, color='r', linestyle='--', alpha=0.3)
        ax2.axhline(y=30, color='g', linestyle='--', alpha=0.3)
        ax2.set_ylabel('RSI')
        
        # Add MACD subplot
        ax3.plot(df.index, df['macd'], label='MACD', color='blue', alpha=0.7)
        ax3.plot(df.index, df['macd_signal'], label='Signal', color='orange', alpha=0.7)
        ax3.set_ylabel('MACD')
        
        # Customize appearance
        ax1.set_title(f"{token_label} Technical Analysis")
        ax1.legend(loc='upper left')
        ax3.legend(loc='upper left')
        
    else:  # simple style
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot price line
        ax.plot(df.index, df['close'], label='Price', color='black', alpha=0.7)
        
        # Add moving averages
        ax.plot(df.index, df['sma10'], '--', label='SMA10', color='blue', alpha=0.7)
        ax.plot(df.index, df['sma50'], '--', label='SMA50', color='orange', alpha=0.7)
        ax.plot(df.index, df['sma200'], '--', label='SMA200', color='red', alpha=0.7)
        
        # Customize appearance
        ax.set_title(f"{token_label} Price Movement")
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    
    # Save chart
    path = os.path.join(CHART_DIR, f"{token_label.lower()}_{style}.png")
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return path

# 4. Content Generation
def generate_token_gpt_content(analysis: dict) -> str:
    """Generate GPT content for a single token analysis."""
    # Format volume based on size
    def format_volume(vol: float) -> str:
        """Format volume based on size and token."""
        name = analysis['name'].lower()
        if name in ['bitcoin', 'btc']:
            return f"${vol/1e9:.2f}B"  # Bitcoin in billions
        elif name in ['ethereum', 'eth']:
            return f"${vol/1e9:.2f}B"  # Ethereum in billions
        elif vol >= 1e9:
            return f"${vol/1e9:.2f}B"
        elif vol >= 1e6:
            return f"${vol/1e6:.2f}M"
        else:
            return f"${vol/1e3:.2f}K"
    
    volume_display = format_volume(analysis['patterns']['volume']['current'])
    volume_avg_display = format_volume(analysis['patterns']['volume']['average'])
    
    prompt = f"""Write a detailed technical analysis for {analysis['name']}.

Price Action:
- Current Price: ${analysis['price']:,.2f}
- Trend: {analysis['patterns']['trend'].title()}
- Volatility: {analysis['patterns']['volatility']:.1f}%

Support/Resistance:
- Support: ${analysis['patterns']['support']:,.2f}
- Resistance: ${analysis['patterns']['resistance']:,.2f}

Volume Analysis:
- Current Volume: {volume_display}
- Average Volume: {volume_avg_display}
- Trend: {analysis['patterns']['volume']['trend']}
- Change: {analysis['patterns']['volume']['change']:.1f}%

Technical Indicators:
- RSI: {analysis['indicators']['rsi']:.1f}
- MACD: {analysis['indicators']['macd']:.3f}
- Signal: {analysis['indicators']['macd_signal']:.3f}
- SMAs: 10=${analysis['indicators']['sma10']:,.2f}, 50=${analysis['indicators']['sma50']:,.2f}, 200=${analysis['indicators']['sma200']:,.2f}

Key Events:
- Golden Cross: {analysis['patterns']['golden_cross']}
- Death Cross: {analysis['patterns']['death_cross']}

Structure the analysis with these sections:
1. Market Overview
2. Volume Analysis
3. Price Structure & Key Levels
4. Technical Indicators
5. Risk Assessment
6. Forward Outlook
"""
    return generate_gpt_text(prompt, max_tokens=2000)

def generate_cross_market_gpt_content(token_analyses: list) -> str:
    """Generate GPT content for cross-market analysis."""
    patterns = [a['patterns'] for a in token_analyses]
    bullish_count = sum(1 for p in patterns if p['trend'] == 'bullish')
    volume_increasing = sum(1 for p in patterns if p['volume']['trend'] == 'increasing')
    btc_analysis = next((a for a in token_analyses if a['name'] == 'Bitcoin'), None)
    
    prompt = f"""Write a comprehensive cross-market analysis using this data:

Market Statistics:
- Bullish tokens: {bullish_count}/{len(token_analyses)}
- Bearish tokens: {len(token_analyses) - bullish_count}/{len(token_analyses)}
- Rising volume: {volume_increasing}/{len(token_analyses)}
- BTC Trend: {btc_analysis['patterns']['trend'] if btc_analysis else 'unknown'}

Structure the analysis with:
1. Market Sentiment Overview
2. Bitcoin's Market Impact
3. Volume Analysis
4. Risk Assessment
5. Forward Outlook

Focus on correlations between assets and market-wide patterns.

End the analysis with this structure:

- Add standard "Not Financial Advice" disclaimer
- Mention following @Web3_Dobie on Twitter/X for daily updates
- Encourage newsletter subscription
- Add signature: "Until next week, Hunter the Web3 Dobie 🐾"
"""
    return generate_gpt_text(prompt, max_tokens=1500)

def generate_ta_substack_article() -> str:
    """Generate complete technical analysis article."""
    logging.info("🔍 Starting TA article generation")
    token_analyses = []
    article_sections = []
    date_str = datetime.now().strftime("%B %d, %Y")
    
    # First analyze BTC to get current data for intro
    btc_df = fetch_ohlcv("BTCUSDT")
    btc_patterns = analyze_token_patterns(btc_df)
    btc_price = btc_df['close'].iloc[-1]
    
    # Generate intro with market-wide focus
    headline = "Weekly Technical Analysis: A Dobie's Deep Dive"
    intro_prompt = f"""Write an engaging 200-word market overview for a crypto technical analysis article dated {date_str}.

Use these market conditions:
- Overall Trend: {btc_patterns['trend']}
- Market Volatility: {btc_patterns['volatility']:.1f}%
- Volume Trend: {btc_patterns['volume']['trend']}
- Key Events: {'Golden Cross detected' if btc_patterns['golden_cross'] else 'Death Cross detected' if btc_patterns['death_cross'] else 'No major crosses'}

Key points to cover:
- General market sentiment this past week
- Notable technical developments across crypto
- Volume trends and what they signal
- Key levels to watch this week
- Potential market-moving events
- Risk factors to consider

Keep the tone professional but engaging.
End with: "Let's dive into the technical analysis for each major token... 🐾"
"""

    intro = generate_gpt_text(intro_prompt, max_tokens=300)
    article_sections.append(f"# {headline}\n\n{intro}\n")
    
    # Analyze each token
    for name, symbol in TOKENS.items():
        logging.info(f"Analyzing {name}...")
        df = fetch_ohlcv(symbol)
        chart_path = generate_chart(df, name.title())
        patterns = analyze_token_patterns(df)
        
        analysis = {
            'name': name.title(),
            'symbol': symbol[:-4],
            'price': df['close'].iloc[-1],
            'chart': chart_path,
            'patterns': patterns,
            'indicators': {
                'sma10': df['close'].rolling(10).mean().iloc[-1],
                'sma50': df['close'].rolling(50).mean().iloc[-1],
                'sma200': df['close'].rolling(200).mean().iloc[-1],
                'rsi': ta.rsi(df['close'], length=14).iloc[-1],
                'macd': ta.macd(df['close'])['MACD_12_26_9'].iloc[-1],
                'macd_signal': ta.macd(df['close'])['MACDs_12_26_9'].iloc[-1]
            }
        }
        token_analyses.append(analysis)
        
        # Generate GPT content for this token
        content = generate_token_gpt_content(analysis)
        article_sections.append(f"\n## {name.title()} Analysis\n\n![Chart]({chart_path})\n\n{content}\n")
    
    # Generate cross-market analysis
    cross_market = generate_cross_market_gpt_content(token_analyses)
    article_sections.append("\n## Cross-Market Analysis\n\n" + cross_market)
    
    # Combine and save
    full_md = "\n".join(article_sections)
    filename = os.path.join(TA_POST_DIR, f"{date_str.replace(' ', '_')}_weekly-ta.md")
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(full_md)
    
    logging.info(f"📝 Article saved to {filename}")

    # Log to Notion
    try:
        log_substack_post_to_notion(f"# {headline}", filename)
        logging.info("✅ Logged TA article to Notion")
    except Exception as e:
        logging.error(f"❌ Notion logging failed: {e}")

    # Send email notification
    try:
        from utils.mailer import send_email_alert
        subject = f"[XAIAgent] TA article ready: {headline}"
        body = (
            f"A TA (Technical Analysis) Substack article has just been generated.\n\n"
            f"Headline: {headline}\n"
            f"Local file path: {filename}\n\n"
            f"Please review and publish this on Substack.\n"
        )
        send_email_alert(subject, body, attachments=[filename])
        logging.info("✉️ Sent email notification")
    except Exception as e:
        logging.error(f"Failed to send TA email alert: {e}")

    return filename

if __name__ == "__main__":
    try:
        # Setup
        for dir_path in [TA_POST_DIR, CHART_DIR]:
            if not os.path.exists(dir_path):
                logging.info(f"Creating directory: {dir_path}")
                os.makedirs(dir_path, exist_ok=True)

        # Test connections
        logging.info("Testing dependencies...")
        test_response = generate_gpt_text("Test GPT connection.", max_tokens=50)
        test_data = fetch_ohlcv("BTCUSDT", limit=1)
        logging.info("✅ All connections successful")

        # Generate content
        filename = generate_ta_substack_article()
        
        # Verify output
        with open(filename, 'r') as f:
            content = f.read()
            if len(content) < 1000:
                raise ValueError("Generated content too short")
            logging.info(f"✅ Generated {len(content)} characters")

    except Exception as e:
        logging.error(f"❌ Generation failed: {str(e)}")
        raise