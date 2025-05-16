import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_API_KEY")
SUBSTACK_DB_ID = os.getenv("NOTION_SUBSTACK_ARCHIVE_DB_ID")
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def log_substack_post_to_notion(headline, filename):
    data = {
        "parent": {"database_id": SUBSTACK_DB_ID},
        "properties": {
            "Headline": {"title": [{"text": {"content": headline}}]},
            "Date": {"date": {"start": datetime.utcnow().isoformat()}},
            "File": {"rich_text": [{"text": {"content": filename}}]},
            "Status": {"select": {"name": "Draft"}}
        }
    }

    response = requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS, json=data)
    if response.status_code == 200:
        print("✅ Logged Substack post to Notion.")
    else:
        print(f"❌ Notion logging failed: {response.status_code}, {response.text}")

