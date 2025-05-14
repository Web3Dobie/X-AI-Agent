
from notion_logger import log_weekly_report
from datetime import datetime

def log_weekly_summary(weekly_growth, top_3_tweet_ids, summary_text):
    log_weekly_report(
        week_ending=datetime.utcnow().date().isoformat(),
        follower_growth=weekly_growth,
        top_tweets="\n".join(top_3_tweet_ids),
        summary=summary_text
    )
