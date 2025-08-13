# crypto_news_bridge.py - Add to your X-AI-Agent scheduler
"""
This integrates with your existing X-AI-Agent scheduler system
to create website-ready crypto news data for DutchBrat.com
"""

import json
import os
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Import your existing X-AI-Agent utilities
from utils.config import DATA_DIR
from utils.gpt import generate_gpt_text
from utils.logging_helper import get_module_logger

logger = get_module_logger(__name__)

class CryptoNewsProcessor:
    def __init__(self):
        self.headline_log = os.path.join(DATA_DIR, "scored_headlines.csv")
        self.output_file = os.path.join(DATA_DIR, "crypto_news_api.json")
    
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
                            headlines.append({
                                'headline': row['headline'],
                                'url': row['url'],
                                'score': float(row['score']),
                                'timestamp': row['timestamp'],
                                'source': row.get('source', 'unknown')
                            })
                    except (ValueError, KeyError) as e:
                        continue
        except FileNotFoundError:
            logger.warning(f"Headline log not found: {self.headline_log}")
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
                    "source": headline_data['source'],
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
        except Exception as e:
            logger.error(f"❌ Error exporting data: {e}")

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

class CryptoNewsProcessor:
    def __init__(self):
        self.headline_log = os.path.join(DATA_DIR, "scored_headlines.csv")
        self.output_file = os.path.join(DATA_DIR, "crypto_news_api.json")
    
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
                            headlines.append({
                                'headline': row['headline'],
                                'url': row['url'],
                                'score': float(row['score']),
                                'timestamp': row['timestamp'],
                                'source': row.get('source', 'unknown')
                            })
                    except (ValueError, KeyError) as e:
                        continue
        except FileNotFoundError:
            print(f"Headline log not found: {self.headline_log}")
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
            print(f"Error generating Hunter comment: {e}")
            return f"📈 This looks significant. Worth watching. — Hunter 🐾"
    
    def process_and_export(self):
        """Process recent headlines and export for website API"""
        print("🔄 Processing top 4 hourly crypto headlines for DutchBrat rotation...")
        
        # Get recent headlines from past hour
        headlines = self.get_recent_headlines(hours=1)
        
        if not headlines:
            print("⚠️ No headlines found in past hour, expanding to 3 hours...")
            # Fallback to last 3 hours if no recent headlines
            headlines = self.get_recent_headlines(hours=3)
        
        if not headlines:
            print("⚠️ No recent headlines found")
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
                    "source": headline_data['source'],
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
            print(f"✅ Crypto news rotation data exported to {self.output_file}")
            print(f"📊 Headlines ready: {len(output_data.get('data', []))}")
        except Exception as e:
            print(f"❌ Error exporting data: {e}")

def main():
    """Main function to run the crypto news processing"""
    processor = CryptoNewsProcessor()
    processor.process_and_export()

if __name__ == "__main__":
    main()