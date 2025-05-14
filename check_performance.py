import os
import csv
import tweepy
from dotenv import load_dotenv

load_dotenv()

client = tweepy.Client(
    bearer_token=os.getenv("BEARER_TOKEN"),
    consumer_key=os.getenv("API_KEY"),
    consumer_secret=os.getenv("API_SECRET"),
    access_token=os.getenv("ACCESS_TOKEN"),
    access_token_secret=os.getenv("ACCESS_TOKEN_SECRET")
)

def fetch_engagement(tweet_id):
    try:
        tweet = client.get_tweet(id=tweet_id, tweet_fields=["public_metrics"])
        metrics = tweet.data['public_metrics']
        return metrics["like_count"], metrics["retweet_count"], metrics["reply_count"]
    except Exception as e:
        print(f"❌ Error fetching {tweet_id}: {e}")
        return 0, 0, 0

# Load tweet log
with open("logs/tweet_log.csv", newline='', encoding='utf-8') as infile, \
     open("logs/performance_log.csv", mode="w", newline='', encoding='utf-8') as outfile:
    reader = csv.DictReader(infile)
    writer = csv.writer(outfile)
    writer.writerow(["tweet_id", "content", "category", "timestamp", "likes", "retweets", "replies"])

    for row in reader:
        likes, retweets, replies = fetch_engagement(row["tweet_id"])
        writer.writerow([
            row["tweet_id"],
            row["content"],
            row["category"],
            row["timestamp"],
            likes,
            retweets,
            replies
        ])
