# jobs/random_post_job.py (Simplified: Original Tweets Only)

import logging
import random
import os

from services.database_service import DatabaseService
from services.hunter_ai_service import get_hunter_ai_service
from utils.x_post import post_tweet
from utils.text_utils import insert_cashtags, insert_mentions

logger = logging.getLogger(__name__)

def run_random_post_job():
    """
    Generates and posts a single, original standalone tweet.
    It prioritizes using a high-scoring XRP headline if one is available and unused.
    Otherwise, it generates a tweet on general market sentiment.
    """
    logger.info("🎲 Starting Random Post Job (Original Tweet Only)...")
    
    db_service = DatabaseService()
    hunter_ai = get_hunter_ai_service()

    try:
        # --- The logic is now only for the "original" tweet path ---
        
        # Check DB for recent XRP tweet to avoid duplicates
        xrp_posted_today = db_service.check_if_content_posted_today('xrp_special_tweet')
        xrp_headline = None
        
        if not xrp_posted_today:
            # Get top XRP headline from the DB
            xrp_headline = db_service.get_top_xrp_headline_for_today()
            if xrp_headline:
                logger.info(f"Using XRP headline from database: {xrp_headline['headline']}")

        if xrp_headline:
            input_text = f"News headline: '{xrp_headline['headline']}' URL: {xrp_headline['url']}"
            task_rules = "TASK: Write a witty, insightful tweet about the provided news headline. Include 1-2 relevant hashtags and end with '— Hunter 🐾'."
            content_type_log = "xrp_special_tweet"
        else:
            input_text = "General crypto market sentiment"
            task_rules = "TASK: Write a standalone, engaging, Web3-native crypto tweet. End with '— Hunter 🐾'."
            content_type_log = "random_original_tweet"

        text = hunter_ai.generate_content(input_text=input_text, task_rules=task_rules, max_tokens=280)
        
        if text:
            text = insert_cashtags(insert_mentions(text))
            post_result = post_tweet(text, category="random")
            
            # Log the post to the database
            if post_result and post_result.get("final_tweet_id"):
                db_service.log_content(
                    content_type=content_type_log,
                    tweet_id=post_result["final_tweet_id"],
                    details=text,
                    headline_id=xrp_headline['id'] if xrp_headline else None,
                    ai_provider=hunter_ai.provider.value
                )
                # Mark headline as used if it was an XRP post
                if xrp_headline:
                    db_service.mark_headline_as_used(xrp_headline['id'])
                logger.info("✅ Random original tweet posted and logged successfully.")
            else:
                logger.error("Failed to post random original tweet.")

    except Exception as e:
        logger.error(f"❌ Failed to complete random post job: {e}", exc_info=True)
        raise