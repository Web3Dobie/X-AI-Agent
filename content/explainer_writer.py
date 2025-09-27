"""
Generate and publish weekly explainer articles.
COMPLETELY REWRITTEN to avoid BaseArticleGenerator temp file issues.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from services.ai_service import get_ai_service
from utils.headline_pipeline import get_top_headline_last_7_days
from utils.publish_substack_article import publish_substack_article

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_substack_explainer():
    """
    Entry point that generates and publishes an explainer article.
    REWRITTEN to bypass BaseArticleGenerator completely.
    """
    try:
        logger.info("📘 Starting explainer article generation and publishing")
        
        # 1. Get headline data
        headline_entry = get_top_headline_last_7_days()
        if not headline_entry:
            logger.warning("⏭ No headlines available for explainer generation")
            raise Exception("No headlines available for explainer generation")
        
        topic = headline_entry["headline"]
        url = headline_entry["url"]
        date_str = datetime.now().strftime("%B %d, %Y")
        
        logger.info(f"📰 Using headline: {topic}")
        
        # 2. Generate content using Gemini
        # --- REVISED, MORE ADVANCED PROMPT ---
        prompt = f"""**ROLE:** You're Hunter 🐾 — a witty Doberman who explains complex crypto topics with personality and insight for a Substack audience.

**TOPIC:** "{topic}"
**SOURCE:** {url}
**DATE:** {date_str}

**TASK:** Write a 1,000–1,500 word article on the topic. Your analysis must be multi-layered to serve three key audiences:
1.  **For Beginners:** Use simple analogies and clearly define all technical terms.
2.  **For Crypto Natives:** Discuss the deeper implications for the ecosystem, tokenomics, or protocol design.
3.  **For Investors:** Analyze the potential market impact and catalysts.

**OUTPUT STRUCTURE:**
- **Subtitle:** "Don't worry: Hunter Explains 🐾"
- **TL;DR:** 3 sharp, insightful bullet points.
- **What's the Deal?:** The core news, explained simply for beginners.
- **Why Does It Matter?:** The deeper analysis for crypto natives and investors.
- **Hunter's Take:** Your unique, witty, and insightful opinion.
- **Bottom Line:** A concise, forward-looking summary.

**TONE:** Inject emojis, sass, and supreme clarity. Your voice is the most important element.
"""
        
        logger.info("🤖 Generating article content with GPT...")
        ai_service = get_ai_service()
        content = ai_service.generate_text(prompt, max_tokens=1800)
        if not content:
            raise Exception("GPT returned no content for explainer article")
        
        logger.info(f"✅ Generated content ({len(content)} characters)")
        
        # 3. Create full article with header and footer
        headline = f"Hunter Explains: {topic}"
        hunter_img_url = "https://w3darticles.blob.core.windows.net/w3d-articles/hunter_headshot.png"
        
        common_footer = """
---

*Follow [@Web3_Dobie](https://twitter.com/Web3_Dobie) for more crypto insights and subscribe for weekly deep dives!*

*This is not financial advice. Always do your own research.*

Until next week,
Hunter the Web3 Dobie 🐾
"""
        
        full_article = f"""![Hunter the Dobie]({hunter_img_url})

# {headline}

{content}

{common_footer}
"""
        
        # 4. Prepare metadata
        summary = f"Hunter breaks down '{topic}' in plain English with wit and insight."
        tags = ["explainer", "crypto", "education", "web3"]
        hunter_image_path = "./content/assets/hunter_poses/explaining.png"
        
        # 5. Publish using the FIXED pipeline (bypasses BaseArticleGenerator completely)
        logger.info("📤 Publishing article using direct pipeline...")
        result = publish_substack_article(
            article_md=full_article,
            headline=headline,
            article_type="explainer",
            tags=tags,
            summary=summary,
            hunter_image_path=hunter_image_path,
            send_email=True
        )
        
        if not result:
            raise Exception("Publication pipeline returned None")
        
        logger.info(f"✅ Explainer article '{headline}' published successfully")
        logger.info(f"🔗 Article URL: {result.get('article_url')}")
        logger.info(f"🐦 Tweet URL: {result.get('tweet_url')}")
        
        # 6. Return result in expected format
        return {
            "headline": topic,  # For backwards compatibility
            "content": "Published successfully",
            "filename": result.get("blob_url", ""),
            "blob_url": result.get("blob_url"),
            "tweet_url": result.get("tweet_url"),
            "article_url": result.get("article_url"),
            "notion_page_id": result.get("notion_page_id")
        }
        
    except Exception as e:
        error_msg = f"Failed to generate explainer article: {str(e)}"
        logger.error(f"❌ {error_msg}")
        raise Exception(error_msg)

# For backwards compatibility - keep the class but make it use the direct function
class ExplainerArticleGenerator:
    """Backwards compatibility wrapper that uses the direct function."""
    
    def generate_and_publish(self):
        return generate_substack_explainer()

if __name__ == "__main__":
    try:
        result = generate_substack_explainer()
        if result:
            print(f"✅ Explainer article generated and published!")
            print(f"Topic: {result['headline']}")
            print(f"Article URL: {result.get('article_url', 'N/A')}")
            print(f"Tweet URL: {result.get('tweet_url', 'N/A')}")
        else:
            print("❌ Failed to generate explainer article")
    except Exception as e:
        print(f"❌ Generation failed: {str(e)}")