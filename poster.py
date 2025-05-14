
from notion_logger import log_tweet
from datetime import datetime

def post_tweet(tweet_text, tweet_type, twitter_client):
    response = twitter_client.create_tweet(text=tweet_text)
    tweet_id = response.data['id']
    tweet_url = f"https://x.com/user/status/{tweet_id}"

    # Placeholder metrics (replace with real metrics gathering logic)
    likes = 0
    retweets = 0
    replies = 0

    engagement_score = likes + 2 * retweets + 3 * replies

    log_tweet(
        date=datetime.utcnow().isoformat(),
        tweet_type=tweet_type,
        url=tweet_url,
        likes=likes,
        retweets=retweets,
        replies=replies,
        engagement_score=engagement_score
    )

    return tweet_id
