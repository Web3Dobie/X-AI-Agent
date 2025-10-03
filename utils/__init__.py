# /app/utils/__init__.py (Refactored)
"""
This file defines the public interface for the 'utils' package.
It now only exposes generic, reusable helper functions and core services
that are still in use after the major refactoring.
"""

# --- Active Core Utilities ---

# X/Twitter posting functions (still in use by jobs, will be moved to a service later)
from .x_post import post_quote_tweet, post_thread, post_tweet, upload_media

# Generic text manipulation helpers
from .text_utils import insert_cashtags, insert_mentions, slugify

# Core monitoring and notification system
from .tg_notifier import send_telegram_message
from .telegram_log_handler import TelegramHandler

# The new rate limit manager for the X poster
from .rate_limit_manager import is_rate_limited, update_rate_limit_state_from_headers


# --- Obsolete imports have been removed ---
# The following have been removed as their logic is now in the `jobs/` or `services/` directories,
# or they were part of the decommissioned file-based/Substack workflow:
#
# - config.py
# - headline_pipeline.py
# - ai_wrappers.py
# - logger.py (the log_tweet function)
# - notion_logger.py (the headline and article functions)
# - mailer.py
# - rotate_logs.py
# - rss_fetch.py
# - scorer.py
# - substack.py
# - blob.py
# - token_helpers.py
# - base_article_generator.py
# - publish_substack_article.py