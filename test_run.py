import os
from dotenv import load_dotenv
import tweepy

import post_utils
import news_poster
from news_poster import post_news_thread

# Load environment variables
load_dotenv()

# Setup Twitter API client
client = tweepy.Client(
    bearer_token=os.getenv("BEARER_TOKEN"),
    consumer_key=os.getenv("API_KEY"),
    consumer_secret=os.getenv("API_SECRET"),
    access_token=os.getenv("ACCESS_TOKEN"),
    access_token_secret=os.getenv("ACCESS_TOKEN_SECRET")
)

# Inject the client into the modules
post_utils.client = client
news_poster.client = client

# Run test
print("🧵 Posting a full news thread...")
post_news_thread()

print("🐦 Posting a single news-based tweet...")
post_utils.post_original_tweet()
