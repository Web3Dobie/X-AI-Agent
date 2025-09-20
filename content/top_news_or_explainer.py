"""
Decision logic to post either the daily opinion thread or generate an explainer article on Fridays.
Fixed version that removes substack_url dependencies.
"""

import logging
import os
from datetime import datetime, timezone

from content.explainer import post_dobie_explainer_thread
from content.opinion_thread import post_top_news_thread
from utils import LOG_DIR, get_module_logger

logger = get_module_logger(__name__)

def post_top_news_or_skip():
    """
    If today is Friday (weekday=4), run the explainer article generation.
    Otherwise, post the top news opinion thread.
    
    Fixed version that removes substack_url dependency.
    """
    today = datetime.now(timezone.utc)
    
    if today.weekday() == 4:  # Friday
        logger.info("📭 Friday detected — running explainer article generation instead of top news reaction.")
        try:
            # Generate explainer article (no substack_url needed anymore)
            post_dobie_explainer_thread()
            logger.info("✅ Explainer article generation completed successfully")
        except Exception as e:
            logger.error(f"❌ Explainer article generation failed: {e}")
            # Re-raise so the job fails properly
            raise
    else:
        logger.info("🔄 Posting top news reaction thread.")
        try:
            post_top_news_thread()
            logger.info("✅ Top news reaction thread completed successfully")
        except Exception as e:
            logger.error(f"❌ Top news reaction thread failed: {e}")
            # Re-raise so the job fails properly
            raise