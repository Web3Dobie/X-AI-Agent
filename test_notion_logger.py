from notion_logger import log_tweet, log_headline, log_weekly_report
from datetime import datetime

# Test log_tweet
log_tweet(
    date=datetime.utcnow().isoformat(),
    tweet_type="Test",
    url="https://x.com/test/status/123456",
    likes=1,
    retweets=2,
    replies=3,
    engagement_score=12
)

# Test log_headline
log_headline(
    date_ingested=datetime.utcnow().isoformat(),
    headline="Test Headline for Logging",
    relevance=7.5,
    viral_score=8.1,
    used=False,
    source_url="https://example.com"
)

# Test log_weekly_report
log_weekly_report(
    week_ending=datetime.utcnow().date().isoformat(),
    follower_growth=42,
    top_tweets="123456\n789012\n345678",
    summary="Test summary: this is a Notion logging test."
)

