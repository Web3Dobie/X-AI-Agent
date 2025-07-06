"""
Generate detailed technical analysis articles for Substack with advanced charting.
Full cloud-native pipeline: Azure Blob, Tweet, Notion logging.
"""

import logging
import os
import re
import openai
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pandas_ta as ta
import requests

from utils.publish_substack_article import publish_substack_article
from utils.blob import upload_to_blob
from utils.notion_logger import log_substack_post_to_notion
from utils.token_helpers import fetch_ohlcv, analyze_token_patterns, generate_chart, generate_risk_assessment
from utils.gpt import generate_gpt_text

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

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_DEPLOYMENT_ID = os.getenv("AZURE_DEPLOYMENT_ID")         # e.g. "gpt-4-turbo"
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2024-02-15-preview")
AZURE_RESOURCE_NAME = os.getenv("AZURE_RESOURCE_NAME")         # e.g. "myazureopenairesource"

openai.api_type = "azure"
openai.api_version = AZURE_API_VERSION
openai.api_key = AZURE_OPENAI_API_KEY
openai.api_base = f"https://{AZURE_RESOURCE_NAME}.openai.azure.com/"

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

# ===== Main Article Generator =====
def generate_ta_substack_article():
    logging.info("🔍 Starting TA article generation")
    token_analyses = []
    article_sections = []
    date_str = datetime.now().strftime("%B %d, %Y")

    # Headline and summary for publishing
    headline = f"Weekly Technical Analysis: {date_str}"
    tags = ["TA", "crypto", "weekly"]
    summary = "A detailed review of this week’s crypto market structure, volume, key levels, and forward outlook."

    hunter_img_url = "https://substackhtd.blob.core.windows.net/web3dobie-substack/hunter_headshot.png"
    article_sections = [f"![Hunter the Dobie]({hunter_img_url})\n"]

    # Market-wide intro (can use GPT)
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
        gpt_content = generate_token_gpt_content(analysis)
        article_sections.append(
            f"\n## {name.title()} Analysis\n\n![Chart]({chart_path})\n\n{gpt_content}\n"
        )

    # Cross-market summary
    cross_market = generate_cross_market_gpt_content(token_analyses)
    article_sections.append("\n## Cross-Market Analysis\n\n" + cross_market)

    # Full markdown article
    article_md = "\n".join(article_sections)

    # ===== PUBLISH VIA NEW PIPELINE =====
    hunter_image_path = "./content/assets/hunter_poses/substack_ta.png"
    publish_substack_article(
        article_md=article_md,
        headline=headline,
        article_type="ta",
        tags=tags,
        summary=summary,
        hunter_image_path=hunter_image_path
    )

    logging.info(f"✅ TA article '{headline}' generated and published.")

if __name__ == "__main__":
    try:
        generate_ta_substack_article()
        print("TA Substack article generation completed.")
    except Exception as e:
        print(f"❌ Generation failed: {str(e)}")
        logging.error(f"❌ Generation failed: {str(e)}")
