import os
import logging
from datetime import datetime
from urllib.parse import quote_plus
import re

# Import your existing utility functions
from utils.substack import send_article_email
from utils.x_post import post_tweet, post_tweet_with_media
from utils.notion_logger import log_substack_post_to_notion, update_notion_page_tweet_url

logger = logging.getLogger(__name__)

def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    # Remove special characters and convert to lowercase
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    # Replace spaces and multiple hyphens with single hyphen
    slug = re.sub(r'[-\s]+', '-', slug)
    # Remove leading/trailing hyphens
    return slug.strip('-')

def generate_filename(headline: str, article_type: str) -> str:
    """Generate filename using existing naming convention"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(headline)
    # Truncate if too long (filesystem limits)
    if len(slug) > 150:
        slug = slug[:150].rstrip('-')
    return f"{date_str}_{slug}.md"

def ensure_posts_directory(article_type: str) -> str:
    """Ensure the posts directory exists and return the path"""
    posts_dir = "/app/posts"  # Container path
    category_dir = os.path.join(posts_dir, article_type)
    
    try:
        os.makedirs(category_dir, exist_ok=True)
        logger.info(f"✅ Ensured directory exists: {category_dir}")
        return category_dir
    except Exception as e:
        logger.error(f"❌ Failed to create directory {category_dir}: {e}")
        raise

def write_article_to_file(article_md: str, filepath: str) -> None:
    """Write article content directly to file with proper error handling"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(article_md)
        
        # Verify file was written successfully
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File was not created: {filepath}")
            
        file_size = os.path.getsize(filepath)
        if file_size == 0:
            raise ValueError(f"File is empty: {filepath}")
            
        logger.info(f"✅ Article written successfully: {filepath} ({file_size} bytes)")
        
    except Exception as e:
        logger.error(f"❌ Failed to write article to {filepath}: {e}")
        # Clean up partial file if it exists
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass
        raise

def publish_substack_article(
    article_md: str,
    headline: str,
    article_type: str = "article",
    tags: list = None,
    summary: str = None,
    hunter_image_path: str = None,
    send_email: bool = False,
    email_recipients: list = None
):
    """
    Publishes an article by saving it directly to the target directory,
    emailing, logging to Notion, and posting to social media.
    
    Fixed version that eliminates temporary file I/O issues.
    """
    try:
        logger.info(f"📘 Starting article publication: {headline}")
        
        # 1. Generate filename and ensure directory exists
        filename = generate_filename(headline, article_type)
        category_dir = ensure_posts_directory(article_type)
        filepath = os.path.join(category_dir, filename)
        
        logger.info(f"📁 Target file: {filepath}")
        
        # 2. Write article directly to final destination
        write_article_to_file(article_md, filepath)
        
        # 3. Send email if requested (using the permanent file)
        if send_email:
            try:
                send_article_email(
                    title=headline,
                    filename=filepath,  # Use the permanent file
                    summary=summary,
                    recipients=email_recipients
                )
                logger.info("📧 Email sent successfully")
            except Exception as e:
                logger.error(f"❌ Email sending failed: {e}")
                # Don't fail the entire publication for email issues
        
        # 4. Generate the file URL for blob storage (local serving)
        blob_url = f"/api/articles/files/{article_type}/{filename}"
        logger.info(f"🔗 Article will be served at: {blob_url}")
        
        # 5. Log to Notion and get the page ID
        notion_page_id = log_substack_post_to_notion(
            headline=headline,
            blob_url=blob_url,
            tweet_url=None,  # Will update after posting tweet
            tags=tags,
            category=article_type,
            summary=summary,
            status="Published"
        )
        
        if not notion_page_id:
            raise Exception("Failed to log article to Notion")
            
        logger.info(f"📝 Logged to Notion with page ID: {notion_page_id}")
        
        # 6. Generate article URL for tweet (using Notion page ID)
        article_app_url = f"https://www.dutchbrat.com/articles?articleId={notion_page_id}"
        
        # 7. Create and post tweet
        tweet_text = (
            f"🚨 New article: {headline}\n\n"
            f"Read it on the archive 👉 {article_app_url}\n"
            "#web3 #crypto"
        )
        
        # Post tweet with or without image
        tweet_url = None
        try:
            if hunter_image_path and os.path.exists(hunter_image_path):
                logger.info(f"📸 Posting tweet with Hunter image: {hunter_image_path}")
                tweet_url = post_tweet_with_media(tweet_text, hunter_image_path, category=f"{article_type}_announcement")
            else:
                if hunter_image_path:
                    logger.warning(f"⚠️ Hunter image not found at {hunter_image_path}")
                logger.info("📝 Posting tweet without image")
                tweet_url = post_tweet(tweet_text, category=f"{article_type}_announcement")
                
            if not tweet_url:
                raise Exception("Tweet posting returned None")
                
            logger.info(f"🐦 Tweet posted: {tweet_url}")
            
        except Exception as e:
            logger.error(f"❌ Tweet posting failed: {e}")
            # This is a critical failure - we should propagate the error
            raise Exception(f"Failed to post announcement tweet: {e}")
        
        # 8. Update Notion entry with tweet URL
        if tweet_url and notion_page_id:
            try:
                update_notion_page_tweet_url(notion_page_id, tweet_url)
                logger.info("✅ Updated Notion with tweet URL")
            except Exception as e:
                logger.error(f"❌ Failed to update Notion with tweet URL: {e}")
                # Don't fail for this - the main publication succeeded
        
        # 9. Return success result
        result = {
            "blob_url": blob_url,
            "tweet_url": tweet_url,
            "article_url": article_app_url,
            "notion_page_id": notion_page_id,
            "filepath": filepath
        }
        
        logger.info(f"✅ Article publication completed successfully!")
        logger.info(f"📄 Article: {article_app_url}")
        logger.info(f"🐦 Tweet: {tweet_url}")
        
        return result
        
    except Exception as e:
        error_msg = f"Failed to publish article '{headline}': {str(e)}"
        logger.error(f"❌ {error_msg}")
        # Re-raise the exception so the job fails properly
        raise Exception(error_msg)

# Example usage (remains unchanged)
if __name__ == "__main__":
    # Test article publication
    test_article = """# Test Article

This is a test article to verify the publication system works correctly.

## Test Section

Content goes here.

---

*Follow [@Web3_Dobie](https://twitter.com/Web3_Dobie) for more crypto insights!*

Until next week,
Hunter the Web3 Dobie 🐾
"""
    
    try:
        result = publish_substack_article(
            article_md=test_article,
            headline="Test Article Publication",
            article_type="explainer",
            tags=["test", "publication"],
            summary="Test article to verify publication system",
            send_email=False
        )
        print("✅ Test publication successful!")
        print(f"Result: {result}")
    except Exception as e:
        print(f"❌ Test publication failed: {e}")