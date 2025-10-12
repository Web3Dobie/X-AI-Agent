# app/jobs/data_ingestion.py
"""
This module contains the self-contained job for ingesting and scoring headlines.
It fetches from RSS, scores/filters in-memory, and inserts high-quality headlines into the database.
This replaces the old workflow spread across utils/rss_fetch.py and utils/scorer.py.
"""

import logging
import re
from typing import List, Dict, Tuple

from services.database_service import DatabaseService
from services.ai_service import get_ai_service
import feedparser
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# --- RSS Fetching (from rss_fetch.py) ---
# -----------------------------------------------------------------------------

def fetch_all_rss_feeds() -> List[Dict]:
    """
    Fetches raw headlines from all configured RSS sources.
    """
    RSS_FEED_URLS = {
        "binance":       "https://www.binance.com/en/feed/news/all",
        "coindesk":      "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "decrypt":       "https://decrypt.co/feed",
        "cryptoslate":   "https://cryptoslate.com/feed/",
        "beincrypto":    "https://www.beincrypto.com/feed/",
        "cointelegraph": "https://cointelegraph.com/rss",
        "bitcoinmag":    "https://bitcoinmagazine.com/feed",
        "cryptobriefing":"https://cryptobriefing.com/feed",
        "theblock":      "https://www.theblock.co/rss.xml",
        "cryptonews":    "https://cryptonews.com/news/feed/",
        "bitcoinist":    "https://bitcoinist.com/feed/",
        "blockchainnews":"https://blockchain.news/RSS",
        "cryptopotato":  "https://cryptopotato.com/feed/",
        "newsbtc":       "https://www.newsbtc.com/feed/",
        "bitcoinnews":   "https://news.bitcoin.com/feed/",    
    }
    
    all_headlines = []
    cutoff_time = datetime.now() - timedelta(hours=2)  # Only get recent articles
    
    for source_name, feed_url in RSS_FEED_URLS.items():
        try:
            logging.info(f"Fetching from {source_name}...")
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:  # Feed parsing error
                logging.warning(f"Error parsing {source_name}: {feed.bozo_exception}")
                continue
            
            for entry in feed.entries[:20]:  # Limit to 20 most recent per source
                try:
                    title = entry.get('title', '').strip()
                    link = entry.get('link', '')
                    
                    # Skip if no title or link
                    if not title or not link:
                        continue
                    
                    # Check if article is recent (optional time filtering)
                    pub_date = entry.get('published_parsed') or entry.get('updated_parsed')
                    if pub_date:
                        article_time = datetime(*pub_date[:6])
                        if article_time < cutoff_time:
                            continue
                    
                    all_headlines.append({
                        "headline": title,
                        "url": link,
                        "source": source_name
                    })
                    
                except Exception as e:
                    logging.debug(f"Error processing entry from {source_name}: {e}")
                    continue
                    
        except Exception as e:
            logging.error(f"Failed to fetch from {source_name}: {e}")
            continue
    
    logging.info(f"Fetched {len(all_headlines)} total headlines from {len(RSS_FEED_URLS)} sources")
    return all_headlines

# -----------------------------------------------------------------------------
# --- Scoring Logic (from scorer.py) ---
# -----------------------------------------------------------------------------

def _extract_ticker(headline: str) -> str:
    """A simple placeholder for your text_utils.extract_ticker function."""
    # Add your real ticker extraction logic here if it's not in a separate utils file.
    match = re.search(r'\$([A-Z]{3,5})\b', headline)
    return match.group(1) if match else ""

def _parse_batch_scores(response: str, expected_count: int) -> List[int]:
    """Parses categories (High, Moderate, Low) and maps them to numerical scores."""
    score_map = {'high': 8, 'moderate': 5, 'low': 2}
    scores = []
    lines = response.strip().split('\n')
    
    for line in lines:
        clean_line = line.strip().lower()
        found_category = None
        if 'high' in clean_line: found_category = 'high'
        elif 'moderate' in clean_line: found_category = 'moderate'
        elif 'low' in clean_line: found_category = 'low'
        scores.append(score_map.get(found_category, score_map['low']))

    if len(scores) < expected_count:
        scores.extend([score_map['low']] * (expected_count - len(scores)))
    elif len(scores) > expected_count:
        scores = scores[:expected_count]
        
    logging.info(f"Mapped {len(scores)} classifications to scores")
    return scores

def _create_batch_prompt(items: List[Dict]) -> Tuple[str, List[Dict]]:
    """Creates a prompt for AI categorization."""
    processed_items = [{
        "headline": item.get("headline", "").replace('"', "'").replace(":", " -"),
        "url": item.get("url", ""),
        "source": item.get("source", ""),
        "ticker": item.get("ticker", "") or _extract_ticker(item.get("headline", ""))
    } for item in items]
    
    headlines_text = "\n".join([f'{i}. {item["headline"]}' for i, item in enumerate(processed_items, 1)])
    
    prompt = f"""You are a content curation assistant.
Your task is to classify the following {len(processed_items)} headlines based on their likely interest to a general crypto audience.
Use one of these three categories: High, Moderate, Low.
Provide your response as a numbered list with only the category name for each headline. Do not include any other text.

HEADLINES:
{headlines_text}

CLASSIFICATION:
"""
    return prompt, processed_items

def _score_and_filter_headlines(items: List[Dict], min_category: str = 'high', batch_size: int = 9) -> List[Dict]:
    """
    Scores headlines in batches and generates Hunter comments for high-scoring ones.
    RETURNS a filtered list of high-scoring headlines with comments.
    """
    if not items: return []
    logging.info(f"Starting batch scoring for {len(items)} headlines...")

    all_accepted_results = []
    ai_service = get_ai_service()
    from services.hunter_ai_service import get_hunter_ai_service
    hunter_ai = get_hunter_ai_service()
    
    category_levels = {'high': 3, 'moderate': 2, 'low': 1}
    min_level = category_levels.get(min_category.lower(), 3)
    system_instruction = "You are a content curation assistant. Classify headlines as High, Moderate, or Low interest. Your entire response must be only a numbered list of these categories."

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        try:
            user_prompt, processed_items = _create_batch_prompt(batch)
            response = ai_service.generate_text(prompt=user_prompt, max_tokens=4096, system_instruction=system_instruction)
            if not response: raise ValueError("API call returned an empty response.")
            scores = _parse_batch_scores(response, len(processed_items))

            for item, score in zip(processed_items, scores):
                current_level = 1
                if score >= 8: current_level = 3
                elif score >= 5: current_level = 2

                if current_level >= min_level:
                    # Generate Hunter comment for high-scoring headlines
                    try:
                        hunter_comment = hunter_ai.generate_headline_comment(item["headline"])
                        logging.debug(f"Generated comment for: {item['headline'][:50]}...")
                    except Exception as e:
                        logging.warning(f"Failed to generate comment for headline: {e}")
                        hunter_comment = None  # Will be generated on-demand later
                    
                    record = {
                        "headline": item["headline"], 
                        "url": item["url"], 
                        "ticker": item["ticker"],
                        "score": score, 
                        "source": item.get("source"),
                        "ai_provider": ai_service.provider.value,
                        "hunter_comment": hunter_comment
                    }
                    all_accepted_results.append(record)
        except Exception as e:
            logging.error(f"Error processing scoring batch: {e}")

    logging.info(f"Scoring complete: {len(all_accepted_results)} total headlines accepted.")
    return all_accepted_results

# -----------------------------------------------------------------------------
# --- Main Job Orchestration ---
# -----------------------------------------------------------------------------

def run_headline_ingestion_job():
    """
    Orchestrates the entire headline ingestion process as a single job.
    This is the function that the scheduler will call.
    """
    logging.info("--- Starting Headline Ingestion Job ---")
    
    # 1. Fetch raw headlines from RSS sources (in-memory)
    raw_headlines = fetch_all_rss_feeds()
    if not raw_headlines:
        logging.info("No headlines fetched from RSS. Job complete.")
        return

    # 2. Score and filter the headlines in-memory (now with comments)
    high_scoring_headlines = _score_and_filter_headlines(raw_headlines, min_category='high')
    
    if not high_scoring_headlines:
        logging.info("No headlines met the minimum score threshold. Job complete.")
        return
        
    # 3. Prepare and insert the filtered headlines with comments into the database
    db_service = DatabaseService()
    
    headlines_to_insert = [
        (h['headline'], h['url'], h.get('source'), h.get('ticker'), h['score'], h['ai_provider'], h.get('hunter_comment'))
        for h in high_scoring_headlines
    ]
    
    inserted_count = db_service.batch_insert_headlines_with_comments(headlines_to_insert)
    
    logging.info(f"--- Headline Ingestion Job Complete ---")
    logging.info(f"Accepted and inserted {inserted_count} new high-scoring headlines with comments into the database.")