"""
GPT-based batch scoring for headlines.
Optimized for Gemini's large context window to score multiple headlines in single API call.
Logs scores to CSV and Notion.
"""
import csv
import logging
import os
import re
from datetime import datetime
from typing import List, Dict, Tuple

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

def parse_batch_scores(response: str, expected_count: int) -> List[int]:
    """
    Parses categories (High, Moderate, Low) from the batch response and maps them to scores.
    """
    # Define the mapping from category to score
    score_map = {
        'high': 8,
        'moderate': 5,
        'low': 2
    }
    
    scores = []
    lines = response.strip().split('\n')
    
    for line in lines:
        clean_line = line.strip().lower()
        
        # Find which category is mentioned in the line
        found_category = None
        if 'high' in clean_line:
            found_category = 'high'
        elif 'moderate' in clean_line:
            found_category = 'moderate'
        elif 'low' in clean_line:
            found_category = 'low'
            
        if found_category:
            scores.append(score_map[found_category])
        else:
            logging.warning(f"Could not classify line: '{line}'. Defaulting to low score.")
            scores.append(score_map['low'])

    # Pad with default scores if response is too short
    if len(scores) < expected_count:
        missing = expected_count - len(scores)
        logging.warning(f"Got {len(scores)} classifications but expected {expected_count}. Adding {missing} default scores.")
        scores.extend([score_map['low']] * missing)
    
    # Truncate if response is too long
    elif len(scores) > expected_count:
        logging.warning(f"Got {len(scores)} classifications but expected {expected_count}. Truncating.")
        scores = scores[:expected_count]
    
    logging.info(f"Extracted {len(scores)} scores from batch classification")
    return scores

def create_batch_prompt(items: List[Dict]) -> Tuple[str, List[Dict]]:
    processed_items = []
    
    # Enrich items with tickers if missing
    for item in items:
        headline = item.get("headline", "")
        url = item.get("url", "")
        ticker = item.get("ticker", "") or extract_ticker(headline)
        
        processed_items.append({
            "headline": headline,
            "url": url,
            "ticker": ticker
        })
    
    # Build a simple, clean list of headlines
    headlines_text = "\n".join([f'{i}. {item["headline"]}' for i, item in enumerate(processed_items, 1)])
    
    # NEW PROMPT: Asks for a category, not a score.
    prompt = f"""You are a content curation assistant.
Your task is to classify the following {len(processed_items)} headlines based on their likely interest to a general crypto audience.

Use one of these three categories: High, Moderate, Low.
Provide your response as a numbered list with only the category name for each headline.

HEADLINES:
{headlines_text}

CLASSIFICATION:
"""
    
    return prompt, processed_items


def score_headlines_batch(items: List[Dict], min_score: int = 7, batch_size: int = 25) -> List[Dict]:
    """
    Score multiple headlines in batches to optimize rate limits while avoiding safety filters.
    
    Args:
        items: List of dicts with 'headline', 'url', 'ticker' (optional) keys
        min_score: Minimum score threshold for inclusion (default: 7)
        batch_size: Number of headlines per batch (default: 25 to avoid safety triggers)
    
    Returns:
        List of scored headline records meeting minimum score threshold
    """
    if not items:
        logging.info("No headlines to score")
        return []
    
    logging.info(f"Starting batch scoring for {len(items)} headlines in batches of {batch_size}")
    
    all_results = []
    
    # Process in smaller batches to avoid safety filters
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(items) + batch_size - 1) // batch_size
        
        logging.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} headlines)")
        
        try:
            # Create batch prompt
            batch_prompt, processed_items = create_batch_prompt(batch)
            
            # Single API call for this batch
            response = generate_gpt_text(batch_prompt, max_tokens=1000)
            
            if not response or "Unable to produce content" in response:
                logging.warning(f"Batch {batch_num} failed, falling back to individual scoring")
                batch_results = score_headlines_individual(batch, min_score)
                all_results.extend(batch_results)
                continue
            
            logging.info(f"Batch {batch_num} response received ({len(response)} chars)")
            
            # Parse scores from response
            scores = parse_batch_scores(response, len(processed_items))
            
            # Process results and filter by minimum score
            timestamp = datetime.utcnow().isoformat()
            
            for item, score in zip(processed_items, scores):
                headline = item["headline"]
                url = item["url"] 
                ticker = item["ticker"]
                
                if score >= min_score:
                    record = {
                        "headline": headline,
                        "url": url,
                        "ticker": ticker,
                        "score": score,
                        "timestamp": timestamp,
                    }
                    
                    # Save to CSV and Notion
                    _append_to_csv(record)
                    notion_log_headline(
                        date_ingested=timestamp,
                        headline=headline,
                        relevance_score=score,
                        viral_score=score,
                        used=False,
                        source_url=url,
                    )
                    
                    all_results.append(record)
                    logging.info(f"Accepted headline (score {score}): '{headline[:60]}...'")
                else:
                    logging.info(f"Rejected headline (score {score}): '{headline[:60]}...'")
            
            logging.info(f"Batch {batch_num} complete: {len([s for s in scores if s >= min_score])}/{len(batch)} headlines accepted")
            
        except Exception as e:
            logging.error(f"Error in batch {batch_num}: {e}")
            logging.info(f"Falling back to individual scoring for batch {batch_num}")
            batch_results = score_headlines_individual(batch, min_score)
            all_results.extend(batch_results)
    
    logging.info(f"All batch scoring complete: {len(all_results)} total headlines accepted")
    return all_results


def score_headlines_individual(items: List[Dict], min_score: int = 7) -> List[Dict]:
    """
    Fallback method: Score headlines individually (original method).
    Used when batch scoring fails.
    """
    results = []
    for item in items:
        headline = item.get("headline", "")
        url = item.get("url", "")
        ticker = item.get("ticker", "") or extract_ticker(headline)

        # Individual prompt
        prompt = (
            "Rate this headline for social media engagement. "
            f"Respond with the score in the format 'X/10'. "
            f'Headline: "{headline}"'
        )
        response = generate_gpt_text(prompt)
        
        # Parse score
        score = extract_score_from_response(response)
        
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

            _append_to_csv(record)
            notion_log_headline(
                date_ingested=timestamp,
                headline=headline,
                relevance_score=score,
                viral_score=score,
                used=False,
                source_url=url,
            )

            logging.info(f"Individual scored headline: '{headline}' -> {score}")
            results.append(record)
        else:
            logging.info(f"Individual rejected headline: '{headline}' -> {score}")

    return results


def score_headlines(items: List[Dict], min_score: int = 7) -> List[Dict]:
    """
    Main scoring function - uses batch scoring by default, falls back to individual.
    
    Args:
        items: list of {'headline': str, 'url': str, 'ticker': str (optional)}
        min_score: minimum score threshold (default: 7)
    
    Returns:
        list of dicts with 'headline', 'url', 'ticker', 'score', 'timestamp'
        only including headlines scoring >= min_score
    """
    # Use batch scoring for efficiency
    return score_headlines_batch(items, min_score)


def _append_to_csv(record: Dict):
    """
    Append a scored record to the CSV file with standardized header.
    """
    file_exists = os.path.exists(SCORED_CSV)
    
    try:
        with open(SCORED_CSV, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["score", "headline", "url", "ticker", "timestamp"])
            
            # Write header if file is new
            if not file_exists:
                writer.writeheader()
                
            writer.writerow({
                "score": record["score"],
                "headline": record["headline"], 
                "url": record["url"],
                "ticker": record["ticker"],
                "timestamp": record["timestamp"],
            })
            
    except Exception as e:
        logging.error(f"Failed to write to CSV: {e}")


def write_headlines(records: List[Dict]):
    """
    Write multiple headline records to CSV (batch write).
    Maintained for backward compatibility.
    """
    if not records:
        return
        
    for record in records:
        _append_to_csv(record)


# Backward compatibility - keep old function name as alias
def score_headlines_old(items: List[Dict], min_score: int = 7) -> List[Dict]:
    """Backward compatibility alias for individual scoring."""
    return score_headlines_individual(items, min_score)