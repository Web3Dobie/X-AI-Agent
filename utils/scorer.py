"""
GPT-based scoring for headlines.
Logs scores to CSV and Notion.
"""
import csv
import logging
import os
import re
from datetime import datetime

from .config import DATA_DIR, LOG_DIR
from .gpt import generate_gpt_text
from .notion_logger import log_headline_to_vault as notion_log_headline
from .text_utils import extract_ticker

# Configure logging
log_file = os.path.join(LOG_DIR, "scorer.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# CSV file to record all scored headlines
SCORED_CSV = os.path.join(DATA_DIR, "scored_headlines.csv")

def extract_score_from_response(response: str) -> int:
    """
    Extracts numerical score from GPT response, handling cases like "8/10" and "8 out of 10".
    
    Args:
        response: Full text response from GPT
    
    Returns:
        Parsed integer score clamped between 1 and 10, or 1 if parsing fails.
    """
    try:
        # Extended regex to match both "X/10" and "X out of 10"
        match = re.search(r"\b([1-9]|10)\s*(?:/|out of)\s*10\b", response, re.IGNORECASE)
        if match:
            score_raw = int(match.group(1))
            return max(1, min(10, score_raw))  # Clamp to [1..10]
        else:
            # If no match, fallback to minimum score
            logging.warning(f"Couldn't find a valid score pattern in response: {response}")
            return 1
    except Exception as e:
        logging.error(f"Error extracting score from response: '{response}'. Error: {e}")
        return 1


def score_headlines(items: list[dict], min_score: int = 7) -> list[dict]:
    """
    Score headlines and only return/save those meeting minimum score threshold.
    
    Args:
        items: list of {'headline': str, 'url': str, 'ticker': str (optional)}
        min_score: minimum score threshold (default: 7)
    
    Returns:
        list of dicts with 'headline', 'url', 'ticker', 'score', 'timestamp'
        only including headlines scoring >= min_score
    """
    results = []
    for item in items:
        headline = item.get("headline", "")
        url = item.get("url", "")
        ticker = item.get("ticker", "")

        # If pipeline didnt supply a ticker, backfill:
        if not ticker:
            ticker = extract_ticker(headline)

        # Formulate prompt (explicitly mention ticker)
        prompt = (
            f"Score this news headline about {ticker} from 1 to 10, based on how likely it is to go viral on Twitter: "
            f"\"{headline}\""
        )
        response = generate_gpt_text(prompt)
        
        # Try parsing response as float, then round to nearest int (clamp to [1..10])
        try:
        #    raw = float(response.strip())
        #    score = int(round(raw))
            score = extract_score_from_response(response)
        except Exception as e:
            logging.error(f"Failed to parse the score from response: {response}. Error: {e}")
            score = 1

        if score < 1:
            score = 1
        elif score > 10:
            score = 10

        # Only process headlines meeting minimum score
        if score >= min_score:
            timestamp = datetime.utcnow().isoformat()
            record = {
                "headline": headline,
                "url": url,
                "ticker": ticker,
                "score": score,
                "timestamp": timestamp,
            }

            # Append to CSV and log to Notion (moved inside if block)
            _append_to_csv(record)
            notion_log_headline(
                date_ingested=timestamp,
                headline=headline,
                relevance_score=score,
                viral_score=score,
                used=False,
                source_url=url,
            )

            logging.info(f"Scored headline: '{headline}' -> {score}")
            results.append(record)
        else:
            logging.info(f"Skipped low-scoring headline: '{headline}' -> {score}")

    return results


def _append_to_csv(record: dict):
    """
    Append a scored record to the CSV file with standardized header.
    """
    try:
        logging.info(f"Attempting to write headline to CSV: '{record.get('headline', '')}'")
        
        header = ["score", "headline", "url", "ticker", "timestamp"]
        os.makedirs(DATA_DIR, exist_ok=True)
        write_header = not os.path.exists(SCORED_CSV)
        
        with open(SCORED_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            if write_header:
                writer.writeheader()
                logging.info(f"Created new CSV file with header at {SCORED_CSV}")
            
            # Ensure all fields are present
            row = {
                "score": record.get("score", 0),
                "headline": record.get("headline", ""),
                "url": record.get("url", ""),
                "ticker": record.get("ticker", ""),
                "timestamp": record.get("timestamp", ""),
            }
            writer.writerow(row)
            logging.info(f"Successfully wrote headline to CSV: '{row['headline']}'")
            
    except PermissionError:
        logging.error(f"Permission denied when writing to {SCORED_CSV}")
        raise
    except IOError as e:
        logging.error(f"IO Error writing to CSV: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error writing to CSV: {str(e)}")
        raise


def write_headlines(records: list[dict]):
    """
    Convenience function to write multiple scored records at once.
    """
    for rec in records:
        # Ensure required keys
        rec.setdefault("url", "")
        rec.setdefault("ticker", "")
        rec.setdefault("timestamp", datetime.utcnow().isoformat())
        _append_to_csv(rec)
        notion_log_headline(
            date_ingested=rec["timestamp"],
            headline=rec["headline"],
            relevance_score=rec["score"],
            viral_score=rec["score"],
            used=False,
            source_url=rec["url"],
        )
