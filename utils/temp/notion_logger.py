import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
TWEET_LOG_DB = os.getenv("NOTION_TWEET_LOG_DB")

notion = Client(auth=NOTION_API_KEY)

def log_to_notion(tweet_id, date, tweet_type, url, likes, retweets, replies, engagement_score):
    notion.pages.create(
        parent={"database_id": TWEET_LOG_DB},
        properties={
            "Tweet ID": {"title": [{"text": {"content": str(tweet_id)}}]},
            "Date": {"date": {"start": date}},
            "Type": {"select": {"name": tweet_type}},
            "URL": {"url": url},
            "Likes": {"number": likes},
            "Retweets": {"number": retweets},
            "Replies": {"number": replies},
            "Engagement Score": {"number": engagement_score}
        }
    )