# /app/utils/config.py

import os
import logging

# This module assumes that Docker Compose's 'env_file' directive has already loaded
# all necessary variables into the environment when the container started.
# We do not need to use the `dotenv` library here.

logger = logging.getLogger(__name__)

# --- Twitter/X API Configuration ---
# These are read directly from the environment populated by Docker Compose.
#
TWITTER_CONSUMER_KEY = os.getenv("X_API_KEY")
TWITTER_CONSUMER_SECRET = os.getenv("X_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")
BOT_USER_ID = os.getenv("X_BOT_USER_ID")

# --- Notion API Configuration ---
#
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_TWEET_LOG_DB = os.getenv("NOTION_TWEET_LOG_DB")
NOTION_SUBSTACK_ARCHIVE_DB_ID = os.getenv("NOTION_SUBSTACK_ARCHIVE_DB_ID") # Used for articles

# --- Database Configuration ---
#
DATABASE_CONFIG = {
    "host": os.getenv('DB_HOST', 'postgres'),
    "port": int(os.getenv('DB_PORT', '5432')),
    "dbname": os.getenv('DB_NAME', 'agents_platform'),
    "user": os.getenv('DB_USER', 'hunter_admin'),
    "password": os.getenv('DB_PASSWORD')
}

# --- Directory Configuration ---
#
LOG_DIR = "/app/logs"
DATA_DIR = "/app/data"
CHART_DIR = "/app/charts"
POSTS_DIR = "/app/posts"
BACKUP_DIR = "/app/backup"

# --- Validate that critical secrets have been loaded ---
if not TWITTER_CONSUMER_KEY or not DATABASE_CONFIG["password"]:
    # This check is still important to ensure the .env files were loaded correctly.
    error_msg = "Critical environment variables are missing. Check that your .env files are correctly referenced in docker-compose.yaml and contain the required values (e.g., X_API_KEY, DB_PASSWORD)."
    logger.critical(error_msg)
    raise ImportError(error_msg)

