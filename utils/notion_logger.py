import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
TWEET_LOG_DB = os.getenv("NOTION_TWEET_LOG_DB")
HEADLINE_VAULT_DB = os.getenv("HEADLINE_VAULT_DB_ID")

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

def log_headline(date_ingested, headline, relevance_score, viral_score, used, source_url):
    notion.pages.create(
        parent={"database_id": HEADLINE_VAULT_DB},
        properties={
            "Headline Vault": {
                "title": [{"text": {"content": headline}}]
            },
            "Date Ingested": {
                "date": {"start": date_ingested}
            },
            "Headline": {
                "rich_text": [{"text": {"content": headline}}]
            },
            "Relevance Score": {
                "number": relevance_score
            },
            "Viral Score": {
                "number": viral_score
            },
            "Used?": {
                "checkbox": used
            },
            "Source": {
                "url": source_url
            }
        }
    )