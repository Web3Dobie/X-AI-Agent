"""
Base class for all Substack article generators.
Fixed version that uses the new publication system and proper error handling.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from utils.publish_substack_article import publish_substack_article

class BaseArticleGenerator(ABC):
    """Abstract base class for all article generators."""
    
    def __init__(self):
        self.date_str = datetime.now().strftime("%B %d, %Y")
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Common configuration
        self.hunter_img_url = "https://w3darticles.blob.core.windows.net/w3d-articles/hunter_headshot.png"
        self.common_footer = """
---

*Follow [@Web3_Dobie](https://twitter.com/Web3_Dobie) for more crypto insights and subscribe for weekly deep dives!*

*This is not financial advice. Always do your own research.*

Until next week,
Hunter the Web3 Dobie 🐾
"""
    
    @abstractmethod
    def _generate_content(self) -> Optional[str]:
        """Generate the main article content. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _get_headline(self) -> str:
        """Get the article headline. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _get_article_type(self) -> str:
        """Get the article type (e.g., 'ta', 'explainer'). Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _get_tags(self) -> List[str]:
        """Get article tags. Must be implemented by subclasses."""
        pass
    
    def _get_summary(self) -> str:
        """Get article summary. Can be overridden by subclasses."""
        return f"Weekly {self._get_article_type()} analysis by Hunter the Web3 Dobie."
    
    def _get_hunter_image_path(self) -> str:
        """Get Hunter's image path. Can be overridden by subclasses."""
        return "./content/assets/hunter_poses/explaining.png"
    
    def _create_full_article(self, content: str) -> str:
        """Create the complete article with header image and footer."""
        headline = self._get_headline()
        
        full_article = f"""![Hunter the Dobie]({self.hunter_img_url})

# {headline}

{content}

{self.common_footer}
"""
        return full_article
    
    def generate_and_publish(self) -> Optional[Dict[str, str]]:
        """
        Main method to generate and publish article.
        Fixed version with proper error handling.
        """
        article_type = self._get_article_type()
        headline = None
        
        try:
            self.logger.info(f"📘 Starting {article_type} article generation and publishing")
            
            # Generate headline first for error reporting
            headline = self._get_headline()
            self.logger.info(f"📝 Article headline: {headline}")
            
            # Generate content
            content = self._generate_content()
            if not content:
                error_msg = f"Failed to generate {article_type} content"
                self.logger.error(f"❌ {error_msg}")
                raise Exception(error_msg)
            
            self.logger.info(f"✅ Generated {article_type} content ({len(content)} characters)")
            
            # Create full article
            full_article = self._create_full_article(content)
            
            # Prepare metadata
            summary = self._get_summary()
            tags = self._get_tags()
            hunter_image_path = self._get_hunter_image_path()
            
            # Publish using unified pipeline
            result = publish_substack_article(
                article_md=full_article,
                headline=headline,
                article_type=self._get_article_type(),
                tags=tags,
                summary=summary,
                hunter_image_path=hunter_image_path,
                send_email=True
            )
            
            if not result:
                error_msg = f"Publication pipeline returned None for {article_type} article"
                self.logger.error(f"❌ {error_msg}")
                raise Exception(error_msg)
            
            self.logger.info(f"✅ {article_type.title()} article '{headline}' published successfully")
            self.logger.info(f"🔗 Article URL: {result.get('article_url')}")
            self.logger.info(f"🐦 Tweet URL: {result.get('tweet_url')}")
            
            return {
                "headline": headline,
                "article_type": self._get_article_type(),
                "blob_url": result.get("blob_url"),
                "tweet_url": result.get("tweet_url"),
                "article_url": result.get("article_url"),
                "notion_page_id": result.get("notion_page_id"),
                "summary": summary,
                "tags": tags
            }
            
        except Exception as e:
            error_msg = f"Failed to publish {article_type} article"
            if headline:
                error_msg += f" '{headline}'"
            error_msg += f": {str(e)}"
            
            self.logger.error(f"❌ {error_msg}")
            
            # Re-raise the exception so the job fails properly
            raise Exception(error_msg)