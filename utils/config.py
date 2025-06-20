from dotenv import load_dotenv
import os
import logging

# Load .env into environment
load_dotenv()

# API keys & secrets
OPENAI_API_KEY        = os.getenv("OPENAI_API_KEY")
NOTION_API_KEY        = os.getenv("NOTION_API_KEY")
HEADLINE_VAULT_DB_ID  = os.getenv("HEADLINE_VAULT_DB_ID")
WEEKLY_REPORT_DB_ID   = os.getenv("WEEKLY_REPORT_DB_ID")
NOTION_TWEET_LOG_DB   = os.getenv("NOTION_TWEET_LOG_DB")
NOTION_SUBSTACK_ARCHIVE_DB_ID = os.getenv("NOTION_SUBSTACK_ARCHIVE_DB_ID")
BOT_USER_ID           = os.getenv("X_BOT_USER_ID")
SUBSTACK_SECRET_EMAIL = os.getenv("SUBSTACK_SECRET_EMAIL")
SUBSTACK_SLUG         = os.getenv("SUBSTACK_SLUG")
SUBSTACK_API_KEY      = os.getenv("SUBSTACK_API_KEY")

# Azure OpenAI credentials
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_DEPLOYMENT_ID = os.getenv("AZURE_DEPLOYMENT_ID")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2024-02-15-preview")
AZURE_RESOURCE_NAME = os.getenv("AZURE_RESOURCE_NAME")

# SUBSTACK_EMAIL        = os.getenv("SUBSTACK_EMAIL")
# SUBSTACK_PASSWORD     = os.getenv("SUBSTACK_PASSWORD")
SUBSTACK_COOKIE       = os.getenv("SUBSTACK_COOKIE")
SUBSTACK_COOKIES_PATH = os.getenv("SUBSTACK_COOKIES_PATH")
SUBSTACK_PUBLICATION_URL = os.getenv("SUBSTACK_PUBLICATION_URL")
EMAIL_USERNAME        = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD        = os.getenv("EMAIL_PASSWORD")

# Twitter credentials
TWITTER_CONSUMER_KEY    = os.getenv("X_API_KEY")
TWITTER_CONSUMER_SECRET = os.getenv("X_API_SECRET")
TWITTER_ACCESS_TOKEN    = os.getenv("X_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET   = os.getenv("X_ACCESS_TOKEN_SECRET")
# (optional) BEARER_TOKEN if used elsewhere:
TWITTER_BEARER_TOKEN    = os.getenv("X_BEARER_TOKEN")

# Local directories
BASE_DIR     = os.path.dirname(os.path.dirname(__file__))
DATA_DIR     = os.path.join(BASE_DIR, "data")
LOG_DIR      = os.path.join(BASE_DIR, "logs")
TA_POST_DIR  = os.path.join(BASE_DIR, "ta_posts")
CHART_DIR    = os.path.join(BASE_DIR, "charts")
BACKUP_DIR   = os.path.join(BASE_DIR, "backup")
SUBSTACK_POST_DIR = os.path.join(BASE_DIR, "substack_posts")

# RSS Feeds for Headlines
RSS_FEED_URLS = {
    "coindesk":      "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "decrypt":       "https://decrypt.co/feed",
    "cryptoslate":   "https://cryptoslate.com/feed/",
    "beincrypto":    "https://www.beincrypto.com/feed/",
    "cointelegraph": "https://cointelegraph.com/rss",
    "bitcoinmag":    "https://bitcoinmagazine.com",
    "cryptobriefing":"https://cryptobriefing.com",
    "theblock":      "https://www.theblockcrypto.com",
    "cryptonews":    "https://cryptonews.com",
    "bitcoinist":    "https://bitcoinist.com",
    "blockchainnews":"https://www.the-blockchain.com",
    "cryptopotato":  "https://cryptopotato.com",
    "newsbtc":       "https://www.newsbtc.com",
    "bitcoinnews":   "https://news.bitcoin.com",
}

