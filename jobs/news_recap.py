# Hunter-Agent/jobs/news_recap.py

import logging
import os
from datetime import datetime

from services.database_service import DatabaseService
from services.ai_service import get_ai_service
from utils.x_post import post_thread, upload_media
from utils.text_utils import insert_cashtags, insert_mentions # Assuming these are in text_utils

logger = logging.getLogger(__name__)

def run_news_thread_job():
    """
    Generates and posts a daily news recap thread based on the top headlines
    from the database.
    """
    logger.info("📰 Starting Daily News Recap Job...")
    db_service = DatabaseService()
    ai_service = get_ai_service()

    try:
        # 1. Get top 3 headlines FROM THE DATABASE
        # This replaces the get_today_headlines() function that read from a CSV.
        top_headlines = db_service.get_top_headlines(count=3, days=1)
        
        if not top_headlines or len(top_headlines) < 3:
            logger.warning("Not enough fresh headlines in the database for a news thread. Skipping.")
            return

        logger.info(f"Selected top 3 headlines for the thread.")
        
        # 2. Generate thread content
        prompt_lines = [f"- {h['headline']}" for h in top_headlines]
        headlines_text = "\n".join(prompt_lines)
        
        task_rules = """
**TASK:** Write a 3-part tweet thread summarizing the key crypto headlines provided.
**RULES:**
- Each tweet must be clever, engaging, and under 280 characters.
- Use relevant emojis and cashtags.
- End each tweet with '— Hunter 🐾'.
- Separate each tweet with '---'.
"""
        thread_parts = ai_service.generate_thread(
            prompt=headlines_text,
            system_instruction=task_rules,
            parts=3,
            max_tokens=2048
        )

        if not thread_parts or len(thread_parts) < 3:
            logger.warning("AI returned insufficient parts for news recap. Skipping.")
            return

        # 3. Format and post the thread
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        header = f"Daily Dobie Headlines [{date_str}] 📰\n\n"
        thread_parts[0] = header + thread_parts[0]
        thread_parts = [insert_mentions(insert_cashtags(p)) for p in thread_parts]
        
        media_id = upload_media("/app/content/assets/hunter_poses/explaining.png")
        
        post_result = post_thread(thread_parts, category="news_summary", media_id_first=media_id)
        
        # 4. Log the result and mark headlines as used
        if post_result and post_result.get("error") is None:
            logger.info("✅ News recap thread posted successfully.")
            final_tweet_id = post_result.get("final_tweet_id")
            full_thread_text = "\n---\n".join(thread_parts)
            
            # Log the entire thread as one piece of content
            db_service.log_content(
                content_type="news_recap_thread",
                tweet_id=final_tweet_id,
                details=full_thread_text,
                headline_id=top_headlines[0]['id'], # Log against the top headline
                ai_provider=ai_service.provider.value
            )
            
            # Mark all used headlines as used to prevent re-use
            for headline in top_headlines:
                db_service.mark_headline_as_used(headline['id'])
        else:
            logger.error(f"Failed to post news recap thread. Error: {post_result.get('error')}")

    except Exception as e:
        logger.error(f"❌ Failed to complete news recap job: {e}", exc_info=True)
        raise