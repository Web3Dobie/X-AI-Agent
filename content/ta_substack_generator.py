"""
Generate detailed technical analysis articles for Substack with advanced charting.
Now uses BaseArticleGenerator for consistency with explainer_writer.py
"""

import os
import sys
import logging
from typing import Dict, List, Any, Optional

# Add the parent directory to Python path so we can import utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    
    def _validate_analysis_data(self, analysis: Dict[str, Any]) -> bool:
        """Validate that analysis data makes sense before sending to GPT."""
        try:
            price = float(analysis['price'])
            support = float(analysis['patterns']['support'])
            resistance = float(analysis['patterns']['resistance'])
            
            # Basic sanity checks
            if price <= 0:
                self.logger.error(f"Invalid price for {analysis['name']}: {price}")
                return False
                
            if support >= resistance:
                self.logger.warning(f"Support >= Resistance for {analysis['name']}: {support} >= {resistance}")
                # Fix the data using dynamic context
                try:
                    # Get 3-month data for better S/R calculation
                    symbol_map = {
                        'Bitcoin': 'BTCUSDT', 'Ethereum': 'ETHUSDT', 'Solana': 'SOLUSDT',
                        'Ripple': 'XRPUSDT', 'Dogecoin': 'DOGEUSDT'
                    }
                    symbol = symbol_map.get(analysis['name'])
                    if symbol:
                        df_3m = fetch_ohlcv(symbol, limit=90)
                        if not df_3m.empty:
                            # Use actual recent low/high as realistic S/R
                            recent_low = df_3m['low'].tail(30).min()  # 30-day low
                            recent_high = df_3m['high'].tail(30).max()  # 30-day high
                            analysis['patterns']['support'] = recent_low
                            analysis['patterns']['resistance'] = recent_high
                        else:
                            # Fallback to percentage-based
                            analysis['patterns']['support'] = price * 0.92
                            analysis['patterns']['resistance'] = price * 1.08
                    else:
                        analysis['patterns']['support'] = price * 0.92
                        analysis['patterns']['resistance'] = price * 1.08
                except Exception:
                    # Final fallback
                    analysis['patterns']['support'] = price * 0.92
                    analysis['patterns']['resistance'] = price * 1.08
                
            # Validate that price is within reasonable bounds of S/R
            if price < support * 0.7 or price > resistance * 1.3:
                self.logger.warning(f"Price outside reasonable S/R range for {analysis['name']}: "
                                  f"Price: {price}, Support: {support}, Resistance: {resistance}")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating analysis data for {analysis['name']}: {e}")
            return False

    def _get_price_context(self, token_name: str, current_price: float) -> str:
        """Get dynamic price context based on 3-month high/low data."""
        try:
            # Map token names to symbols
            symbol_map = {
                'Bitcoin': 'BTCUSDT',
                'Ethereum': 'ETHUSDT', 
                'Solana': 'SOLUSDT',
                'Ripple': 'XRPUSDT',
                'Dogecoin': 'DOGEUSDT'
            }
            
            symbol = symbol_map.get(token_name)
            if not symbol:
                return "at current levels"
            
            # Fetch 3 months of daily data (roughly 90 days)
            df_3m = fetch_ohlcv(symbol, limit=90)
            if df_3m.empty:
                return "at current levels"
            
            # Calculate 3-month high and low
            high_3m = df_3m['high'].max()
            low_3m = df_3m['low'].min()
            
            # Calculate percentiles to determine position
            price_range = high_3m - low_3m
            if price_range == 0:
                return "at current levels"
            
            # Calculate where current price sits in the 3-month range
            position = (current_price - low_3m) / price_range
            
            # Determine context based on position
            if position <= 0.25:
                distance_from_low = ((current_price - low_3m) / low_3m) * 100
                return f"near 3-month lows ({distance_from_low:.1f}% above low of ${low_3m:,.2f})"
            elif position >= 0.75:
                distance_from_high = ((high_3m - current_price) / high_3m) * 100
                return f"near 3-month highs ({distance_from_high:.1f}% below high of ${high_3m:,.2f})"
            else:
                percentile = position * 100
                return f"in mid-range ({percentile:.0f}th percentile of 3-month range ${low_3m:,.2f}-${high_3m:,.2f})"
                
        except Exception as e:
            self.logger.warning(f"Could not calculate price context for {token_name}: {e}")
            return "at current levels"

    def _create_data_summary(self) -> str:
        """Create a data summary for validation and context."""
        summary = f"\n=== LIVE DATA SUMMARY ({self.date_str}) ===\n"
        
        for analysis in self.token_analyses:
            price_context = self._get_price_context(analysis['name'], analysis['price'])
            summary += f"{analysis['name']}: ${analysis['price']:,.2f} ({price_context}), {analysis['patterns']['trend']} trend\n"
        
        return summary
    
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
        """Generate GPT content for a single token analysis with strict data constraints."""
        volume_display = self._format_volume(analysis['patterns']['volume']['current'])
        volume_avg_display = self._format_volume(analysis['patterns']['volume']['average'])
        price_context = self._get_price_context(analysis['name'], analysis['price'])

        # Create very specific prompt that forces GPT to use only the provided data
        prompt = f"""You are a crypto technical analyst. Write ONLY about the data provided below. Do NOT use any historical prices or trends from your training data.

CURRENT LIVE DATA for {analysis['name']} as of {self.date_str}:
- Current Price: ${analysis['price']:,.2f} (USE ONLY THIS PRICE)
- Price Context: {price_context}
- Price Trend: {analysis['patterns']['trend'].title()} 
- Volatility: {analysis['patterns']['volatility']:.1f}%
- Support Level: ${analysis['patterns']['support']:,.2f}
- Resistance Level: ${analysis['patterns']['resistance']:,.2f}
- Current Volume: {volume_display}
- Average Volume: {volume_avg_display}
- Volume Trend: {analysis['patterns']['volume']['trend']}
- RSI: {analysis['indicators']['rsi']:.1f}
- MACD: {analysis['indicators']['macd']:.3f}
- 10-day SMA: ${analysis['indicators']['sma10']:,.2f}
- 50-day SMA: ${analysis['indicators']['sma50']:,.2f}

STRICT RULES:
1. ONLY use the exact prices and data provided above
2. Do NOT mention any other price levels not listed
3. Do NOT reference historical events or timeframes beyond the price context provided
4. Focus on the current technical setup only
5. If trend is "bullish", describe bullish conditions; if "bearish", describe bearish conditions
6. Use the price context to explain whether current levels are significant
7. Keep analysis factual and data-driven

Write a technical analysis covering:
- Current price action and where it sits in recent range
- Support/resistance levels analysis
- Volume interpretation 
- Technical indicator signals
- Trading outlook based on the data

Maximum 300 words."""

        return generate_gpt_text(prompt, max_tokens=400)
    
    def _generate_cross_market_analysis_content(self) -> str:
        """Generate cross-market analysis with strict data validation."""
        if not self.token_analyses:
            return "Cross-market analysis unavailable due to insufficient data."
            
        patterns = [a['patterns'] for a in self.token_analyses]
        bullish_count = sum(1 for p in patterns if p['trend'] == 'bullish')
        bearish_count = len(self.token_analyses) - bullish_count
        volume_increasing = sum(1 for p in patterns if p['volume']['trend'] == 'increasing')
        btc_analysis = next((a for a in self.token_analyses if a['name'] == 'Bitcoin'), None)

        # Build explicit data summary
        token_summary = []
        for analysis in self.token_analyses:
            token_summary.append(
                f"- {analysis['name']}: ${analysis['price']:,.2f}, {analysis['patterns']['trend']} trend"
            )

        prompt = f"""Write a cross-market analysis using ONLY the data below from {self.date_str}.

CURRENT MARKET DATA:
{chr(10).join(token_summary)}

MARKET STATISTICS:
- Bullish tokens: {bullish_count}/{len(self.token_analyses)}
- Bearish tokens: {bearish_count}/{len(self.token_analyses)}
- Tokens with rising volume: {volume_increasing}/{len(self.token_analyses)}
- BTC trend: {btc_analysis['patterns']['trend'] if btc_analysis else 'unknown'}
- BTC price: {f"${btc_analysis['price']:,.2f}" if btc_analysis else "$0.00"}

STRICT RULES:
1. ONLY use the exact prices and data listed above
2. Do NOT reference any historical prices or events
3. Base all analysis on the current trend data provided
4. If most tokens are bullish, describe bullish market conditions
5. If most tokens are bearish, describe bearish market conditions
6. Reference specific current prices when discussing tokens

Structure: Market Sentiment Overview, Bitcoin's Current Impact, Volume Trends, Forward Outlook

End with: "Follow @Web3_Dobie for more insights! This is not financial advice."

Maximum 400 words."""

        return generate_gpt_text(prompt, max_tokens=500)
    
    def _generate_market_overview(self) -> str:
        """Generate market overview with strict current data constraints."""
        btc_df = fetch_ohlcv("BTCUSDT")
        btc_patterns = analyze_token_patterns(btc_df)
        btc_price = btc_df['close'].iloc[-1]
        
        prompt = f"""Write a brief market overview for {self.date_str}.

CURRENT LIVE DATA ONLY:
- BTC Price: ${btc_price:,.2f}
- BTC Trend: {btc_patterns['trend']}
- BTC Volatility: {btc_patterns['volatility']:.1f}%

RULES:
1. ONLY reference the current BTC price of ${btc_price:,.2f}
2. Do NOT mention any other price levels
3. Keep it to 2-3 sentences about current market conditions
4. Base sentiment on the actual trend data provided

Write a market overview that sets the tone for technical analysis."""

        return generate_gpt_text(prompt, max_tokens=200)
    
    def _generate_content(self) -> Optional[str]:
        """Generate the complete TA article content with data validation."""
        try:
            # Build article sections
            article_sections = []
            
            # Market overview with strict current data
            intro = self._generate_market_overview()
            if intro:
                article_sections.append(f"{intro}\n")
            
            # Analyze all tokens with validation
            self.token_analyses = []
            for name, symbol in self.tokens.items():
                analysis = self._analyze_token(name, symbol)
                
                # Validate data before using
                if self._validate_analysis_data(analysis):
                    self.token_analyses.append(analysis)
                    
                    gpt_content = self._generate_token_analysis_content(analysis)
                    article_sections.append(
                        f"\n## {name.title()} Analysis\n\n"
                        f"![{name.title()} Chart]({analysis['chart']})\n\n"
                        f"{gpt_content}\n"
                    )
                else:
                    self.logger.error(f"Skipping {name} due to invalid data")
            
            # Add data summary for debugging
            data_summary = self._create_data_summary()
            self.logger.info(data_summary)
            
            # Cross-market analysis with validated data
            cross_market = self._generate_cross_market_analysis_content()
            article_sections.append("\n## Cross-Market Analysis\n\n" + cross_market)
            
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
        # Try multiple possible paths for Hunter images
        possible_paths = [
            "./content/assets/hunter_poses/substack_ta.png",
            "./content/assets/hunter_poses/explaining.png", 
            "./content/assets/hunter_poses/waving.png",
            "./assets/hunter_poses/substack_ta.png",
            "./images/hunter_poses/substack_ta.png"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                self.logger.info(f"Using Hunter image: {path}")
                return path
        
        self.logger.warning("No Hunter images found - posting without image")
        return None

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