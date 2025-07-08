"""
Generate detailed technical analysis articles for Substack with advanced charting.
Full cloud-native pipeline: Azure Blob, Tweet, Notion logging.
"""

import logging
import os
from datetime import datetime

import pandas_ta as ta
import pandas as pd

from utils.publish_substack_article import publish_substack_article
from utils.blob import upload_to_blob
from utils.notion_logger import log_substack_post_to_notion
from utils.token_helpers import fetch_ohlcv, analyze_token_patterns, generate_chart
from utils.gpt import generate_gpt_text  # ✅ uses Azure-configured OpenAI SDK
from utils.substack import send_article_email

# ===== Config =====
TA_POST_DIR = os.getenv("TA_POST_DIR", "./ta_posts")
CHART_DIR = os.path.join(TA_POST_DIR, "charts")
os.makedirs(CHART_DIR, exist_ok=True)
os.makedirs(TA_POST_DIR, exist_ok=True)

log_file = os.path.join(TA_POST_DIR, "ta_substack_generator.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

TOKENS = {
    "bitcoin": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "solana": "SOLUSDT",
    "ripple": "XRPUSDT",
    "dogecoin": "DOGEUSDT",
}


def generate_token_gpt_content(analysis: dict) -> str:
    """Generate GPT content for a single token analysis."""
    def format_volume(vol: float) -> str:
        name = analysis['name'].lower()
        if name in ['bitcoin', 'btc', 'ethereum', 'eth'] or vol >= 1e9:
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

Structure the analysis with:
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

End with:
- 'Not Financial Advice' disclaimer
- Follow @Web3_Dobie for updates
- Subscribe CTA
- Sign off: "Until next week, Hunter the Web3 Dobie 🐾"
"""
    return generate_gpt_text(prompt, max_tokens=1500)


def generate_ta_substack_article():
    logging.info("🔍 Starting TA article generation")
    token_analyses = []
    article_sections = []
    date_str = datetime.now().strftime("%B %d, %Y")

    # Header content
    headline = f"Weekly Technical Analysis: {date_str}"
    summary = "A detailed review of this week’s crypto market structure, volume, key levels, and forward outlook."
    tags = ["TA", "crypto", "weekly"]
    hunter_img_url = "https://substackhtd.blob.core.windows.net/web3dobie-substack/hunter_headshot.png"
    article_sections.append(f"![Hunter the Dobie]({hunter_img_url})\n")

    # Market overview
    btc_df = fetch_ohlcv("BTCUSDT")
    btc_patterns = analyze_token_patterns(btc_df)
    intro_prompt = (
        f"Write a market overview for a crypto TA article on {date_str}. "
        f"BTC trend: {btc_patterns['trend']}, "
        f"volatility: {btc_patterns['volatility']:.1f}%, "
        f"volume trend: {btc_patterns['volume']['trend']}."
    )
    intro = generate_gpt_text(intro_prompt, max_tokens=300)
    article_sections.append(f"# {headline}\n\n{intro}\n")

    # Token-specific analysis
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
        gpt_content = generate_token_gpt_content(analysis)
        article_sections.append(
            f"\n## {name.title()} Analysis\n\n![Chart]({chart_path})\n\n{gpt_content}\n"
        )

    # Cross-market wrap-up
    cross_market = generate_cross_market_gpt_content(token_analyses)
    article_sections.append("\n## Cross-Market Analysis\n\n" + cross_market)

    # Combine article
    article_md = "\n".join(article_sections)

    # Publish
    hunter_image_path = "./content/assets/hunter_poses/substack_ta.png"
    publish_substack_article(
        article_md=article_md,
        headline=headline,
        article_type="ta",
        tags=tags,
        summary=summary,
        hunter_image_path=hunter_image_path,
        send_email=True,
        email_recipients=None
    )

    logging.info(f"✅ TA article '{headline}' generated and published.")


if __name__ == "__main__":
    try:
        generate_ta_substack_article()
        print("TA Substack article generation completed.")
    except Exception as e:
        print(f"❌ Generation failed: {str(e)}")
        logging.error(f"❌ Generation failed: {str(e)}")
