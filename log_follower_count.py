import os
import csv
import tweepy
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

client = tweepy.Client(
    bearer_token=os.getenv("BEARER_TOKEN"),
    consumer_key=os.getenv("API_KEY"),
    consumer_secret=os.getenv("API_SECRET"),
    access_token=os.getenv("ACCESS_TOKEN"),
    access_token_secret=os.getenv("ACCESS_TOKEN_SECRET")
)

DISABLED_UNTIL = datetime.fromisoformat("2025-05-14T10:34:52")

def log_follower_count():
    if datetime.utcnow() < DISABLED_UNTIL:
        print(f"⏸️ Follower logging paused until {DISABLED_UNTIL} UTC.")
        return

    try:
        user = client.get_me(user_auth=True)
        user_id = user.data.id
        followers = client.get_user(id=user_id, user_fields=["public_metrics"]).data.public_metrics["followers_count"]

        os.makedirs("logs", exist_ok=True)
        with open("logs/follower_log.csv", mode="a", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(["timestamp", "followers"])
            writer.writerow([datetime.utcnow().isoformat(), followers])
        print(f"✅ Logged follower count: {followers}")
    except Exception as e:
        print(f"❌ Failed to log follower count: {e}")