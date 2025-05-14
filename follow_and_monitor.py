import os
import tweepy
from dotenv import load_dotenv

# Load credentials
load_dotenv()

# Authenticate
client = tweepy.Client(
    bearer_token=os.getenv("BEARER_TOKEN"),
    consumer_key=os.getenv("API_KEY"),
    consumer_secret=os.getenv("API_SECRET"),
    access_token=os.getenv("ACCESS_TOKEN"),
    access_token_secret=os.getenv("ACCESS_TOKEN_SECRET")
)

# Key opinion leaders in Web3 & crypto
key_accounts = [
    "VitalikButerin", "balajis", "cdixon", "naval", "brian_armstrong",
    "jessewldn", "santiagoroel", "twobitidiot", "ljxie", "CryptoHayes",
    "tarunchitra", "packyM", "owocki", "DefiantNews", "MessariCrypto"
]

# Follow accounts and print latest tweets
for username in key_accounts:
    try:
        user = client.get_user(username=username)
        user_id = user.data.id

        # Follow the user
        client.follow_user(target_user_id=user_id)
        print(f"✅ Followed: {username}")

        # Get recent tweets
        tweets = client.get_users_tweets(id=user_id, max_results=5)
        print(f"📝 Latest tweets from @{username}:")
        if tweets.data:
            for tweet in tweets.data:
                print("   -", tweet.text[:200])  # Limit to first 200 characters
        else:
            print("   (No recent tweets)")
    except Exception as e:
        print(f"⚠️ Error with {username}: {e}")

