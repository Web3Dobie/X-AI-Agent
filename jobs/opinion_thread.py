# jobs/opinion_thread.py

import logging
import os
import re  # ADDED
import requests
from datetime import datetime

from services.database_service import DatabaseService
from services.hunter_ai_service import get_hunter_ai_service
from utils.x_post import post_thread, upload_media
from utils.text_utils import insert_cashtags, insert_mentions

logger = logging.getLogger(__name__)

def _is_valid_url(url: str) -> bool:
    """Checks if a URL is accessible."""
    if not url: return False
    try:
        resp = requests.head(url, allow_redirects=True, timeout=5)
        return resp.status_code == 200
    except requests.RequestException:
        return False

def run_opinion_thread_job():
    """
    Generates and posts a "Hunter Reacts" thread based on the top daily headline.
    """
    logger.info("🔥 Starting 'Hunter Reacts' Opinion Thread Job...")
    db_service = DatabaseService()
    hunter_ai = get_hunter_ai_service()

    try:
        # 1. Get top headline from database
        headline_entry = db_service.get_top_headline(days=1)
        
        if not headline_entry:
            logger.warning("No suitable headline found for opinion thread. Skipping.")
            return

        headline_text = headline_entry["headline"]
        headline_id = headline_entry["id"]
        headline_url = headline_entry["url"]
        logger.info(f"Selected top headline (ID: {headline_id}): '{headline_text}'")

        # 2. Generate thread with updated signature
        thread_prompt = f"""
React to this crypto headline with bold, clever, Web3-native commentary:

"{headline_text}"

Write a 3-part tweet thread with emojis, snark, and wit.
Use relevant hashtags where appropriate.
"""
        
        system_instruction = """
Create a reaction thread that:
- Analyzes the implications of the news
- Adds witty commentary and insights
- Ends each tweet with '— Hunter 🐾'
- Separates tweets with '---'
- Do NOT add any preamble, introduction, or meta-commentary
- Do NOT number tweets or use labels like "Tweet 1:", "Tweet 2:"
- Start directly with the content
"""
        
        thread_parts = hunter_ai.generate_thread(
            prompt=thread_prompt,
            parts=3,
            max_tokens=2000,
            system_instruction=system_instruction
        )

        if not thread_parts or len(thread_parts) < 3:
            logger.warning("AI returned insufficient parts for opinion thread. Skipping.")
            return

        # ADDED: Clean up AI-added preambles and labels
        cleaned_parts = []
        for i, part in enumerate(thread_parts):
            cleaned = part.strip()
            
            # Remove common preambles (only from first part)
            if i == 0:
                # Remove introductory phrases
                cleaned = re.sub(
                    r'^(Okay,?\s*)?(here\'s|here is)\s*(a|the)\s*\d*-?part\s*.+?(thread|tweet|response).{0,50}?:?\s*',
                    '',
                    cleaned,
                    flags=re.IGNORECASE
                )
            
            # Remove tweet labels from all parts
            cleaned = re.sub(r'^\*?\*?Tweet\s*\d+:?\*?\*?\s*', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'^(Part|Thread)\s*\d+:?\s*', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'^\d+[\.)]\s*', '', cleaned)  # Remove "1. " or "1) "
            
            cleaned_parts.append(cleaned.strip())
        
        thread_parts = cleaned_parts

        # 3. Format and post the thread
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        thread_parts[0] = f"🔥 Hunter Reacts [{date_str}]\n\n" + thread_parts[0]
        
        # Append URL to the last part if valid
        if _is_valid_url(headline_url):
            thread_parts[-1] = thread_parts[-1].strip() + f" 🔗 {headline_url}"
        else:
            logger.warning(f"Skipping broken URL for headline: {headline_text}")

        # Final formatting
        thread_parts = [insert_cashtags(insert_mentions(p)) for p in thread_parts]
        
        # Upload Hunter's waving pose
        try:
            media_id = upload_media("/app/content/assets/hunter_poses/waving.png")
        except Exception as e:
            logger.warning(f"Failed to upload image: {e}")
            media_id = None
        
        post_result = post_thread(thread_parts, category="news_opinion", media_id_first=media_id)

        # 4. Log result and mark headline as used
        if post_result and post_result.get("error") is None:
            logger.info("✅ Opinion thread posted successfully.")
            final_tweet_id = post_result.get("final_tweet_id")
            full_thread_text = "\n---\n".join(thread_parts)
            
            db_service.log_content(
                content_type="opinion_thread",
                tweet_id=final_tweet_id,
                details=full_thread_text,
                headline_id=headline_id,
                ai_provider=hunter_ai.provider.value
            )
            
            db_service.mark_headline_as_used(headline_id)
        else:
            logger.error(f"Failed to post opinion thread. Error: {post_result.get('error')}")

    except Exception as e:
        logger.error(f"❌ Failed to complete opinion thread job: {e}", exc_info=True)
        raise