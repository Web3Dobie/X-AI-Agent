# jobs/explainer_thread.py

import logging
import os
from datetime import datetime

from services.database_service import DatabaseService
from services.hunter_ai_service import get_hunter_ai_service
from utils.x_post import post_thread, upload_media
from utils.text_utils import slugify
from utils.notion_logger import log_article_to_notion, update_notion_article_with_tweet_url

logger = logging.getLogger(__name__)

def run_explainer_thread_job():
    """
    Generates a detailed explainer article with Hunter's voice, saves it locally, 
    logs it to Notion, and posts a promotional thread on X that links to it.
    """
    logger.info("Starting Full Explainer Job (Article + Thread)...")
    db_service = DatabaseService()
    hunter_ai = get_hunter_ai_service()

    try:
        # 1. Get top headline from the database
        headline_entry = db_service.get_top_headline(days=7)
        if not headline_entry:
            logger.warning("No suitable headline found for the explainer. Skipping.")
            return

        topic = headline_entry["headline"]
        headline_id = headline_entry["id"]
        logger.info(f"Selected top headline (ID: {headline_id}): '{topic}'")

        # 2. Generate the core article content
        # Note: Hunter persona is now handled by hunter_ai_service automatically
        article_prompt = f"""
Write a 1,000-1,500 word article on: "{topic}"

Your analysis must serve three audiences:
1. **Beginners:** Simple analogies, clear definitions
2. **Crypto Natives:** Ecosystem implications, protocol design
3. **Investors:** Market impact and catalysts

**STRUCTURE:**
- **Subtitle:** "Don't worry: Hunter Explains"
- **TL;DR:** 3 sharp, insightful bullet points
- **What's the Deal?:** Core news explained simply
- **Why Does It Matter?:** Deeper implications
- **Hunter's Take:** Your unique opinion
- **Bottom Line:** Forward-looking summary

Use emojis strategically and inject personality throughout.
"""
        
        article_body = hunter_ai.generate_analysis(article_prompt, max_tokens=3500)

        if not article_body:
            logger.error("AI failed to generate article content. Skipping job.")
            return
        
        # 3. Format the full article with header, image, and footer
        article_title = f"Hunter Explains: {topic}"
        hunter_headshot_url = "https://w3darticles.blob.core.windows.net/w3d-articles/hunter_headshot.png"
        
        common_footer = """
---

*Follow [@Web3_Dobie](https://twitter.com/Web3_Dobie) for more crypto insights and subscribe for weekly deep dives!*

*This is not financial advice. Always do your own research.*

Until next week,
Hunter the Web3 Dobie
"""
        
        final_article_content = f"![Hunter the Dobie]({hunter_headshot_url})\n\n# {article_title}\n\n{article_body}\n\n{common_footer}"
        
        # 4. Save the final article to a local file
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        slug = slugify(topic)
        file_name = f"{today_str}_{slug}.md"
        article_path = f"/app/posts/explainer/{file_name}"
        os.makedirs(os.path.dirname(article_path), exist_ok=True)
        
        with open(article_path, 'w', encoding='utf-8') as f:
            f.write(final_article_content)
        logger.info(f"Article saved locally to: {article_path}")

        # 5. Construct the public URL for the raw file
        public_file_url = f"https://dutchbrat.com/articles/explainer/{file_name}"

        # 6. Log the article to Notion to get a Page ID
        notion_page_id = log_article_to_notion(
            headline=article_title,
            file_url=public_file_url,
            tags=["explainer", "crypto", "education"],
            category="Explainer",
            summary=f"Hunter breaks down '{topic}' with wit and insight."
        )
        
        # 7. Construct the final website URL using the Notion Page ID
        final_website_url = f"https://dutchbrat.com/articles?articleId={notion_page_id}" if notion_page_id else public_file_url

        # 8. Generate and post the promotional thread
        thread_prompt = f"""
Topic: {topic}

Create a 3-part Twitter thread called 'Hunter Explains' about this topic.
Make it simple, clever, and accessible. Use emojis and bold takes.
Each tweet must be under 280 characters.
Do NOT include headers, links, or dates - they will be added separately.
"""
        
        thread_parts = hunter_ai.generate_thread(thread_prompt, parts=3)

        if not thread_parts or len(thread_parts) < 3:
            logger.warning("AI returned insufficient parts for the thread. Skipping post.")
            return

        # Add header to first tweet and link to last tweet
        header = f"Hunter Explains [{today_str}]\n\n"
        thread_parts[0] = header + thread_parts[0].lstrip()
        thread_parts[-1] = thread_parts[-1].strip() + f"\n\nRead the full deep dive: {final_website_url}"

        # Upload Hunter's explaining image
        img_path = "/app/content/assets/hunter_poses/explaining.png"
        media_id = upload_media(img_path) if os.path.exists(img_path) else None
        
        post_result = post_thread(thread_parts, category="explainer", media_id_first=media_id)

        # 9. Log everything and update Notion with the tweet URL
        if post_result and post_result.get("error") is None:
            final_tweet_id = post_result.get("final_tweet_id")
            tweet_url = f"https://x.com/user/status/{final_tweet_id}"
            
            if notion_page_id:
                update_notion_article_with_tweet_url(notion_page_id, tweet_url)
            
            db_service.log_content(
                content_type="explainer_thread", 
                tweet_id=final_tweet_id,
                details=final_article_content, 
                headline_id=headline_id,
                ai_provider=hunter_ai.provider.value, 
                notion_url=final_website_url
            )
            
            db_service.mark_headline_as_used(headline_id)
            logger.info(f"Successfully posted explainer thread and article for: {topic}")
        else:
            logger.error(f"Failed to post explainer thread. Error: {post_result.get('error')}")

    except Exception as e:
        logger.error(f"Failed to complete explainer pipeline: {e}", exc_info=True)
        raise