"""
Generate and publish weekly explainer articles for Substack.
Now uses BaseArticleGenerator for consistency.
"""

import logging
from typing import Dict, List, Optional

from utils.base_article_generator import BaseArticleGenerator
from utils.gpt import generate_gpt_text
from utils.headline_pipeline import get_top_headline_last_7_days

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExplainerArticleGenerator(BaseArticleGenerator):
    """Generates explainer articles based on top weekly headlines."""
    
    def __init__(self):
        super().__init__()
        self.headline_data = None
    
    def _get_headline_data(self) -> Optional[Dict[str, str]]:
        """Fetch the top headline from the last 7 days."""
        if self.headline_data:
            return self.headline_data
            
        headline_entry = get_top_headline_last_7_days()
        if not headline_entry:
            self.logger.warning("⏭ No headlines available for explainer generation")
            return None
        
        self.headline_data = {
            'topic': headline_entry["headline"],
            'url': headline_entry["url"]
        }
        return self.headline_data
    
    def _generate_content(self) -> Optional[str]:
        """Generate the main article content using GPT."""
        headline_data = self._get_headline_data()
        if not headline_data:
            return None
        
        topic = headline_data['topic']
        url = headline_data['url']
        
        prompt = f"""
You're Hunter 🐾 — a witty Doberman who explains complex crypto topics in plain English with personality and insight.

Write a 1,000–1,500 word Substack article about:
"{topic}"

Use this format:
- Subtitle: "Don't worry: Hunter Explains 🐾"
- TL;DR (3 bullets)
- What's the deal?
- Why does it matter?
- Hunter's take
- Bottom line

Inject emojis, sass, and clarity. Reference the source: {url}
Today is {self.date_str}.
"""
        
        article = generate_gpt_text(prompt, max_tokens=1800)
        if not article:
            self.logger.warning("⚠️ GPT returned no content for explainer article")
            return None
        
        return article
    
    def _get_headline(self) -> str:
        """Get the article headline."""
        headline_data = self._get_headline_data()
        if not headline_data:
            return f"Hunter Explains: Weekly Crypto Update - {self.date_str}"
        
        return f"Hunter Explains: {headline_data['topic']}"
    
    def _get_article_type(self) -> str:
        """Get the article type."""
        return "explainer"
    
    def _get_tags(self) -> List[str]:
        """Get article tags."""
        return ["explainer", "crypto", "education", "web3"]
    
    def _get_summary(self) -> str:
        """Get article summary."""
        headline_data = self._get_headline_data()
        if not headline_data:
            return "Hunter breaks down the week's top crypto story in plain English."
        
        return f"Hunter breaks down '{headline_data['topic']}' in plain English with wit and insight."
    
    def _get_hunter_image_path(self) -> str:
        """Get Hunter's image path for explainer articles."""
        return "./content/assets/hunter_poses/explaining.png"

def generate_substack_explainer():
    """
    Entry point for backwards compatibility.
    Now generates AND publishes the article using the unified pipeline.
    """
    generator = ExplainerArticleGenerator()
    result = generator.generate_and_publish()
    
    if result:
        # Return format for backwards compatibility
        headline_data = generator._get_headline_data()
        topic = headline_data['topic'] if headline_data else "Weekly Update"
        
        return {
            "headline": topic,  # For backwards compatibility
            "content": "Published to Substack",  # Changed since we don't return raw content
            "filename": result.get("blob_url", ""),  # Use blob URL instead of local file
            "blob_url": result.get("blob_url"),
            "tweet_url": result.get("tweet_url")
        }
    
    return None

if __name__ == "__main__":
    try:
        result = generate_substack_explainer()
        if result:
            print(f"✅ Explainer article generated and published!")
            print(f"Topic: {result['headline']}")
            print(f"Blob URL: {result.get('blob_url', 'N/A')}")
            print(f"Tweet URL: {result.get('tweet_url', 'N/A')}")
        else:
            print("❌ Failed to generate explainer article")
    except Exception as e:
        print(f"❌ Generation failed: {str(e)}")
        logger.error(f"❌ Generation failed: {str(e)}")