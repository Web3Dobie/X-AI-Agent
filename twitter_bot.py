import os
import tweepy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create a tweepy Client (v2)
client = tweepy.Client(
    bearer_token=os.getenv("BEARER_TOKEN"),
    consumer_key=os.getenv("API_KEY"),
    consumer_secret=os.getenv("API_SECRET"),
    access_token=os.getenv("ACCESS_TOKEN"),
    access_token_secret=os.getenv("ACCESS_TOKEN_SECRET")
)

# Post a tweet
response = client.create_tweet(text="Hello Twitter from Web_Dobie via (API v2) 🤖")
print("Tweeted:", response)

