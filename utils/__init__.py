# utils/__init__.py
import os
from datetime import datetime

# --- Configuration & paths ---
from utils.config import LOG_DIR, SUBSTACK_POST_DIR, DATA_DIR, CHART_DIR, TA_POST_DIR, BACKUP_DIR

# --- Headline pipeline ---
from utils.headline_pipeline import get_top_headline_last_7_days, fetch_and_score_headlines

# --- X/Twitter posting ---
from utils.x_post import post_quote_tweet, post_thread, post_tweet, upload_media

# --- GPT wrappers ---
from utils.gpt import generate_gpt_text, generate_gpt_thread, generate_gpt_tweet

# --- Tweet metrics logging & limits ---
from utils.logging_helper import get_module_logger
from utils.logger import log_tweet
from utils.limit_guard import has_reached_daily_limit

# --- Notion logging ---
from utils.notion_logger import log_substack_post_to_notion, log_headline_to_vault, log_to_notion_tweet

# --- Email & notifications ---
from utils.mailer import send_email_alert

# --- Log rotation ---
from utils.rotate_logs import clear_xrp_flag, rotate_logs

# --- RSS & headline pipeline ---
from utils.rss_fetch import fetch_headlines

# --- Scoring & logging headlines ---
from utils.scorer import score_headlines, write_headlines

# --- Text utilities ---
from utils.text_utils import insert_cashtags, insert_mentions

# --- Telegram handler ---
from utils.tg_notifier import send_telegram_message
from utils.telegram_log_handler import TelegramHandler

# --- Substack utilities ---
from utils.substack import save_article, send_article_email

# --- Blob storage ---
from utils.blob import upload_to_blob

# --- Token helpers (for TA functionality) ---
from utils.token_helpers import fetch_ohlcv, analyze_token_patterns, generate_chart