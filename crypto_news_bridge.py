# crypto_news_bridge.py - Complete version with source extraction and proper logging
"""
This integrates with your existing X-AI-Agent scheduler system
to create website-ready crypto news data for DutchBrat.com
FIXED: All print() statements replaced with proper logging.
"""

import json
import os
import csv
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from urllib.parse import urlparse

# Import your existing X-AI-Agent utilities
from utils.config import DATA_DIR
from utils.gpt import generate_gpt_text
from utils.logging_helper import get_module_logger

logger = get_module_logger(__name__)

class CryptoNewsProcessor:
    def __init__(self):
        self.headline_log = os.path.join(DATA_DIR, "scored_headlines.csv")
        self.output_file = os.path.join(DATA_DIR, "crypto_news_api.json")
    
    def extract_source_from_url(self, url: str) -> str:
        """Extract clean source name from URL"""
        try:
            domain = urlparse(url).netloc.lower()
            
            # Map domains to clean source names
            source_map = {
                'decrypt.co': 'decrypt',
                'cointelegraph.com': 'cointelegraph', 
                'coindesk.com': 'coindesk',
                'beincrypto.com': 'beincrypto',
                'cryptoslate.com': 'cryptoslate',
                'bitcoinmagazine.com': 'bitcoin_magazine',
                'theblock.co': 'the_block',
                'cryptobriefing.com': 'crypto_briefing',
                'cryptonews.com': 'crypto_news',
                'bitcoinist.com': 'bitcoinist',
                'newsbtc.com': 'newsbtc',
                'news.bitcoin.com': 'bitcoin_news',
                'cryptopotato.com': 'crypto_potato',
                'the-blockchain.com': 'blockchain_news',
                'binance.com': 'binance'
            }
            
            # Remove www. prefix
            domain = domain.replace('www.', '')
            
            # Return mapped name or extract first part of domain
            return source_map.get(domain, domain.split('.')[0])
            
        except Exception as e:
            logger.warning(f"Error extracting source from URL {url}: {e}")
            return 'unknown'
    
    def get_recent_headlines(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get recent headlines from the last N hours (default 1 hour for better rotation)"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        headlines = []
        
        try:
            with open(self.headline_log, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        timestamp = datetime.fromisoformat(row['timestamp'])
                        if timestamp > cutoff_time:
                            # Extract source from URL since it's not in CSV
                            source = self.extract_source_from_url(row['url'])
                            
                            headlines.append({
                                'headline': row['headline'],
                                'url': row['url'],
                                'score': float(row['score']),
                                'timestamp': row['timestamp'],
                                'source': source  # Now extracted from URL
                            })
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Error processing headline row: {e}")
                        continue
        except FileNotFoundError:
            logger.warning(f"Headline log not found: {self.headline_log}")
            return []
        except Exception as e:
            logger.error(f"Error reading headline log: {e}")
            return []
        
        # Sort by score (highest first) and return top 4 for 15-min rotation
        headlines.sort(key=lambda x: x['score'], reverse=True)
        return headlines[:4]
    
    def generate_hunter_comment(self, headline: str) -> str:
        """Generate Hunter's tweet-like comment for a headline"""
        prompt = f"""
        You are Hunter, an AI crypto analyst dog who gives short, witty commentary on crypto news.
        Write a brief 1-2 sentence comment about this headline in Hunter's voice.
        Use emojis, be insightful but casual, and end with "— Hunter 🐾"
        
        Headline: {headline}
        
        Comment:
        """
        
        try:
            comment = generate_gpt_text(prompt, max_tokens=100)
            # Ensure it ends with Hunter's signature
            if "— Hunter 🐾" not in comment:
                comment += " — Hunter 🐾"
            return comment.strip()
        except Exception as e:
            logger.error(f"Error generating Hunter comment: {e}")
            return f"📈 This looks significant. Worth watching. — Hunter 🐾"
    
    def process_and_export(self):
        """Process recent headlines and export for website API"""
        logger.info("🔄 Processing top 4 hourly crypto headlines for DutchBrat rotation...")
        
        try:
            # Get recent headlines from past hour
            headlines = self.get_recent_headlines(hours=1)
            
            if not headlines:
                logger.info("⚠️ No headlines found in past hour, expanding to 3 hours...")
                # Fallback to last 3 hours if no recent headlines
                headlines = self.get_recent_headlines(hours=3)
            
            if not headlines:
                logger.warning("⚠️ No recent headlines found")
                # Create empty structure
                output_data = {
                    "success": True,
                    "data": [],
                    "lastUpdated": datetime.now().isoformat(),
                    "message": "No recent crypto news available",
                    "rotationSchedule": "15min intervals"
                }
            else:
                # Generate Hunter comments for top 4 headlines
                processed_news = []
                for headline_data in headlines[:4]:  # Top 4 for 15-min rotation
                    try:
                        hunter_comment = self.generate_hunter_comment(headline_data['headline'])
                        
                        processed_news.append({
                            "headline": headline_data['headline'],
                            "url": headline_data['url'],
                            "score": headline_data['score'],
                            "timestamp": headline_data['timestamp'],
                            "source": headline_data['source'],  # Now properly extracted
                            "hunterComment": hunter_comment
                        })
                    except Exception as e:
                        logger.error(f"Error processing headline: {headline_data.get('headline', 'unknown')}: {e}")
                        continue
                
                output_data = {
                    "success": True,
                    "data": processed_news,
                    "lastUpdated": datetime.now().isoformat(),
                    "totalHeadlines": len(headlines),
                    "rotationSchedule": "15min intervals",
                    "message": f"Top {len(processed_news)} headlines ready for rotation"
                }
            
            # Save to JSON file that the website API can read
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
                
                with open(self.output_file, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)
                logger.info(f"✅ Crypto news rotation data exported to {self.output_file}")
                logger.info(f"📊 Headlines ready: {len(output_data.get('data', []))}")
                
                # Log sources for debugging
                if output_data.get('data'):
                    sources = [item['source'] for item in output_data['data']]
                    logger.debug(f"🔍 Sources extracted: {sources}")
                    
            except Exception as e:
                logger.error(f"❌ Error exporting data: {e}")
                raise  # Re-raise to let scheduler know the job failed
                
        except Exception as e:
            logger.error(f"❌ Error in crypto news processing: {e}")
            raise  # Re-raise to let scheduler know the job failed

# Create the processor instance
crypto_processor = CryptoNewsProcessor()

def generate_crypto_news_for_website():
    """
    Function to be called by the scheduler.
    Processes crypto headlines for DutchBrat website rotation.
    """
    try:
        crypto_processor.process_and_export()
    except Exception as e:
        logger.error(f"Error in crypto news processing: {e}")
        raise

# Legacy processor class for backward compatibility (also fixed with logging)
class CryptoNewsProcessorLegacy:
    def __init__(self):
        self.headline_log = os.path.join(DATA_DIR, "scored_headlines.csv")
        self.output_file = os.path.join(DATA_DIR, "crypto_news_api.json")
    
    def extract_source_from_url(self, url: str) -> str:
        """Extract clean source name from URL"""
        try:
            domain = urlparse(url).netloc.lower()
            
            # Map domains to clean source names (same as above)
            source_map = {
                'decrypt.co': 'decrypt',
                'cointelegraph.com': 'cointelegraph', 
                'coindesk.com': 'coindesk',
                'beincrypto.com': 'beincrypto',
                'cryptoslate.com': 'cryptoslate',
                'bitcoinmagazine.com': 'bitcoin_magazine',
                'theblock.co': 'the_block',
                'cryptobriefing.com': 'crypto_briefing',
                'cryptonews.com': 'crypto_news',
                'bitcoinist.com': 'bitcoinist',
                'newsbtc.com': 'newsbtc',
                'news.bitcoin.com': 'bitcoin_news',
                'cryptopotato.com': 'crypto_potato',
                'the-blockchain.com': 'blockchain_news',
                'binance.com': 'binance'
            }
            
            # Remove www. prefix
            domain = domain.replace('www.', '')
            
            # Return mapped name or extract first part of domain
            return source_map.get(domain, domain.split('.')[0])
            
        except Exception as e:
            logger.debug(f"Error extracting source from URL {url}: {e}")  # Debug level for legacy
            return 'unknown'
    
    def get_recent_headlines(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get recent headlines from the last N hours (default 1 hour for better rotation)"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        headlines = []
        
        try:
            with open(self.headline_log, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        timestamp = datetime.fromisoformat(row['timestamp'])
                        if timestamp > cutoff_time:
                            # Extract source from URL since it's not in CSV
                            source = self.extract_source_from_url(row['url'])
                            
                            headlines.append({
                                'headline': row['headline'],
                                'url': row['url'],
                                'score': float(row['score']),
                                'timestamp': row['timestamp'],
                                'source': source
                            })
                    except (ValueError, KeyError) as e:
                        continue
        except FileNotFoundError:
            logger.debug(f"Headline log not found: {self.headline_log}")
            return []
        
        # Sort by score (highest first) and return top 4 for 15-min rotation
        headlines.sort(key=lambda x: x['score'], reverse=True)
        return headlines[:4]
    
    def generate_hunter_comment(self, headline: str) -> str:
        """Generate Hunter's tweet-like comment for a headline"""
        prompt = f"""
        You are Hunter, an AI crypto analyst dog who gives short, witty commentary on crypto news.
        Write a brief 1-2 sentence comment about this headline in Hunter's voice.
        Use emojis, be insightful but casual, and end with "— Hunter 🐾"
        
        Headline: {headline}
        
        Comment:
        """
        
        try:
            comment = generate_gpt_text(prompt, max_tokens=100)
            # Ensure it ends with Hunter's signature
            if "— Hunter 🐾" not in comment:
                comment += " — Hunter 🐾"
            return comment.strip()
        except Exception as e:
            logger.debug(f"Error generating Hunter comment: {e}")
            return f"📈 This looks significant. Worth watching. — Hunter 🐾"
    
    def process_and_export(self):
        """Process recent headlines and export for website API"""
        logger.info("🔄 Processing top 4 hourly crypto headlines for DutchBrat rotation...")
        
        # Get recent headlines from past hour
        headlines = self.get_recent_headlines(hours=1)
        
        if not headlines:
            logger.info("⚠️ No headlines found in past hour, expanding to 3 hours...")
            # Fallback to last 3 hours if no recent headlines
            headlines = self.get_recent_headlines(hours=3)
        
        if not headlines:
            logger.warning("⚠️ No recent headlines found")
            # Create empty structure
            output_data = {
                "success": True,
                "data": [],
                "lastUpdated": datetime.now().isoformat(),
                "message": "No recent crypto news available",
                "rotationSchedule": "15min intervals"
            }
        else:
            # Generate Hunter comments for top 4 headlines
            processed_news = []
            for headline_data in headlines[:4]:  # Top 4 for 15-min rotation
                hunter_comment = self.generate_hunter_comment(headline_data['headline'])
                
                processed_news.append({
                    "headline": headline_data['headline'],
                    "url": headline_data['url'],
                    "score": headline_data['score'],
                    "timestamp": headline_data['timestamp'],
                    "source": headline_data['source'],  # Now properly extracted
                    "hunterComment": hunter_comment
                })
            
            output_data = {
                "success": True,
                "data": processed_news,
                "lastUpdated": datetime.now().isoformat(),
                "totalHeadlines": len(headlines),
                "rotationSchedule": "15min intervals",
                "message": f"Top {len(processed_news)} headlines ready for rotation"
            }
        
        # Save to JSON file that the website API can read
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Crypto news rotation data exported to {self.output_file}")
            logger.info(f"📊 Headlines ready: {len(output_data.get('data', []))}")
            
            # Log sources for debugging
            if output_data.get('data'):
                sources = [item['source'] for item in output_data['data']]
                logger.debug(f"🔍 Sources extracted: {sources}")
                
        except Exception as e:
            logger.error(f"❌ Error exporting data: {e}")

def main():
    """Main function to run the crypto news processing"""
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    processor = CryptoNewsProcessorLegacy()
    processor.process_and_export()

if __name__ == "__main__":
    main()