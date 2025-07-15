"""
Generate detailed technical analysis articles for Substack with advanced charting.
Now uses BaseArticleGenerator for consistency with explainer_writer.py
"""

import logging
from typing import Dict, List, Any, Optional

import pandas as pd
import pandas_ta as ta

from utils.base_article_generator import BaseArticleGenerator
from utils.token_helpers import fetch_ohlcv, analyze_token_patterns, generate_chart
from utils.gpt import generate_gpt_text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
TOKENS = {
    "bitcoin": "BTCUSDT",
    "ethereum": "ETHUSDT", 
    "solana": "SOLUSDT",
    "ripple": "XRPUSDT",
    "dogecoin": "DOGEUSDT",
}

class TechnicalAnalysisGenerator(BaseArticleGenerator):
    """Generates technical analysis articles with charts and cross-market analysis."""
    
    def __init__(self):
        super().__init__()
        self.tokens = TOKENS
        self.token_analyses = []
    
    def _format_volume(self, vol: float) -> str:
        """Format volume for display."""
        if vol >= 1e9:
            return f"${vol/1e9:.2f}B"
        elif vol >= 1e6:
            return f"${vol/1e6:.2f}M"
        else:
            return f"${vol/1e3:.2f}K"
    
    def _analyze_token(self, name: str, symbol: str) -> Dict[str, Any]:
        """Analyze a single token and return comprehensive data."""
        self.logger.info(f"Analyzing {name}...")
        
        df = fetch_ohlcv(symbol)
        chart_path = generate_chart(df, name.title())
        patterns = analyze_token_patterns(df)
        
        return {
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
    
    def _generate_token_analysis_content(self, analysis: Dict[str, Any]) -> str:
        """Generate GPT content for a single token analysis."""
        volume_display = self._format_volume(analysis['patterns']['volume']['current'])
        volume_avg_display = self._format_volume(analysis['patterns']['volume']['average'])

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

Technical Indicators:
- RSI: {analysis['indicators']['rsi']:.1f}
- MACD: {analysis['indicators']['macd']:.3f}
- SMAs: 10=${analysis['indicators']['sma10']:,.2f}, 50=${analysis['indicators']['sma50']:,.2f}

Structure with: Market Overview, Volume Analysis, Price Structure, Technical Indicators, Outlook
"""
        return generate_gpt_text(prompt, max_tokens=2000)
    
    def _generate_cross_market_analysis_content(self) -> str:
        """Generate cross-market analysis section."""
        if not self.token_analyses:
            return "Cross-market analysis unavailable due to insufficient data."
            
        patterns = [a['patterns'] for a in self.token_analyses]
        bullish_count = sum(1 for p in patterns if p['trend'] == 'bullish')
        volume_increasing = sum(1 for p in patterns if p['volume']['trend'] == 'increasing')
        btc_analysis = next((a for a in self.token_analyses if a['name'] == 'Bitcoin'), None)

        prompt = f"""Write a comprehensive cross-market analysis:

Market Statistics:
- Bullish tokens: {bullish_count}/{len(self.token_analyses)}
- Rising volume: {volume_increasing}/{len(self.token_analyses)}
- BTC Trend: {btc_analysis['patterns']['trend'] if btc_analysis else 'unknown'}

Structure: Market Sentiment, Bitcoin Impact, Volume Analysis, Risk Assessment, Forward Outlook
End with disclaimer and follow @Web3_Dobie + subscribe CTA
"""
        return generate_gpt_text(prompt, max_tokens=1500)
    
    def _generate_market_overview(self) -> str:
        """Generate the market overview section."""
        btc_df = fetch_ohlcv("BTCUSDT")
        btc_patterns = analyze_token_patterns(btc_df)
        
        prompt = (
            f"Write a market overview for crypto TA on {self.date_str}. "
            f"BTC trend: {btc_patterns['trend']}, volatility: {btc_patterns['volatility']:.1f}%"
        )
        return generate_gpt_text(prompt, max_tokens=300)
    
    def _generate_content(self) -> Optional[str]:
        """Generate the complete TA article content."""
        try:
            # Build article sections
            article_sections = []
            
            # Market overview
            intro = self._generate_market_overview()
            if intro:
                article_sections.append(f"{intro}\n")
            
            # Analyze all tokens and generate individual sections
            self.token_analyses = []
            for name, symbol in self.tokens.items():
                analysis = self._analyze_token(name, symbol)
                self.token_analyses.append(analysis)
                
                gpt_content = self._generate_token_analysis_content(analysis)
                article_sections.append(
                    f"\n## {name.title()} Analysis\n\n"
                    f"![{name.title()} Chart]({analysis['chart']})\n\n"
                    f"{gpt_content}\n"
                )
            
            # Cross-market analysis
            cross_market = self._generate_cross_market_analysis_content()
            article_sections.append("\n## Cross-Market Analysis\n\n" + cross_market)
            
            # Combine all sections
            return "\n".join(article_sections)
            
        except Exception as e:
            self.logger.error(f"❌ Error generating TA content: {e}")
            return None
    
    def _get_headline(self) -> str:
        """Get the article headline."""
        return f"Weekly Technical Analysis: {self.date_str}"
    
    def _get_article_type(self) -> str:
        """Get the article type."""
        return "ta"
    
    def _get_tags(self) -> List[str]:
        """Get article tags."""
        return ["TA", "crypto", "weekly"]
    
    def _get_summary(self) -> str:
        """Get article summary."""
        return "A detailed review of this week's crypto market structure, volume, key levels, and forward outlook."
    
    def _get_hunter_image_path(self) -> str:
        """Get Hunter's image path for TA articles."""
        return "./content/assets/hunter_poses/substack_ta.png"

def generate_ta_substack_article():
    """
    Entry point for backwards compatibility.
    Now uses the unified BaseArticleGenerator pipeline.
    """
    generator = TechnicalAnalysisGenerator()
    result = generator.generate_and_publish()
    
    if result:
        logger.info(f"✅ TA article '{result['headline']}' generated and published.")
        return result
    else:
        logger.error("❌ Failed to generate TA article")
        return None

if __name__ == "__main__":
    try:
        result = generate_ta_substack_article()
        if result:
            print("✅ TA Substack article generation completed.")
            print(f"Headline: {result['headline']}")
            print(f"Blob URL: {result.get('blob_url', 'N/A')}")
            print(f"Tweet URL: {result.get('tweet_url', 'N/A')}")
        else:
            print("❌ TA generation failed.")
    except Exception as e:
        print(f"❌ Generation failed: {str(e)}")
        logger.error(f"❌ Generation failed: {str(e)}")