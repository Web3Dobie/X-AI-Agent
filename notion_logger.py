
import os
from notion_client import Client
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

notion = Client(auth=os.getenv("NOTION_TOKEN"))

TWEET_LOG_DB_ID = os.getenv("TWEET_LOG_DB_ID")
HEADLINE_VAULT_DB_ID = os.getenv("HEADLINE_VAULT_DB_ID")
WEEKLY_REPORT_DB_ID = os.getenv("WEEKLY_REPORT_DB_ID")

def log_tweet(date, tweet_type, url, likes, retweets, replies, engagement_score):
    notion.pages.create(parent={"database_id": TWEET_LOG_DB_ID},
        properties={
            "Date": {"date": {"start": date}},
            "Type": {"select": {"name": tweet_type}},
            "URL": {"url": url},
            "Likes": {"number": likes},
            "Retweets": {"number": retweets},
            "Replies": {"number": replies},
            "Engagement Score": {"number": engagement_score}
        })

def log_headline(date_ingested, headline, relevance, viral_score, used, source_url):
    notion.pages.create(parent={"database_id": HEADLINE_VAULT_DB_ID},
        properties={
            "Date Ingested": {"date": {"start": date_ingested}},
            "Headline": {"rich_text": [{"text": {"content": headline}}]},
            "Relevance Score": {"number": relevance},
            "Viral Score": {"number": viral_score},
            "Used?": {"checkbox": used},
            "Source": {"url": source_url}
        })

def log_weekly_report(week_ending, follower_growth, top_tweets, summary):
    notion.pages.create(parent={"database_id": WEEKLY_REPORT_DB_ID},
        properties={
            "Week Ending": {"date": {"start": week_ending}},
            "Follower Growth": {"number": follower_growth},
            "Top Tweets": {"rich_text": [{"text": {"content": top_tweets}}]},
            "Summary": {"rich_text": [{"text": {"content": summary}}]}
        })

# Optional utility if needed in the future
def current_utc_iso():
    return datetime.now(timezone.utc).isoformat()
