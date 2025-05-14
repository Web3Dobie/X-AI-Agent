
from notion_logger import log_headline
from datetime import datetime

def score_and_log_headline(headline_text, relevance_score, viral_score, source_url):
    log_headline(
        date_ingested=datetime.utcnow().isoformat(),
        headline=headline_text,
        relevance=relevance_score,
        viral_score=viral_score,
        used=True,
        source_url=source_url
    )
