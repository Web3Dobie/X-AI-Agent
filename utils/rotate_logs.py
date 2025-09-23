"""
Rotate key CSVs and logs weekly by moving them into dated subfolders under BACKUP_DIR.
Handles rolling retention for scored headlines and weekly rotation for other logs.
FIXED: Robust timestamp parsing for mixed formats in CSV files.
"""

import os
import shutil
import csv
from datetime import datetime, timedelta
import pandas as pd
import logging

from .config import BACKUP_DIR, DATA_DIR, LOG_DIR

logger = logging.getLogger(__name__)

# Ensure backup directory exists
os.makedirs(BACKUP_DIR, exist_ok=True)

# List of log files to rotate weekly
LOG_FILES = [
    "gpt.log",
    "content.market_summary.log",
    "content.news_recap.log",
    "content.opinion_thread.log",
    "content.ta_poster.log",
    "utils.rss_fetch.log",
    "notion_logger.log",
    "x_post_http.log"
]

def safe_timestamp_parse(ts_str):
    """
    Robust timestamp parsing to handle mixed formats:
    - ISO format with T: "2025-09-23T10:56:37.770231"
    - Space format: "2025-06-08 23:05:13.907245"
    """
    try:
        ts_str = str(ts_str).strip()
        if 'T' in ts_str:
            # Handle ISO format - replace T with space and parse
            clean_ts = ts_str.replace('T', ' ')
            return pd.to_datetime(clean_ts)
        else:
            # Handle space format directly
            return pd.to_datetime(ts_str)
    except Exception as e:
        logger.warning(f"Failed to parse timestamp '{ts_str}': {e}")
        # Return NaT (Not a Time) for invalid timestamps
        return pd.NaT

def rotate_file(src, headers=None, rolling=False):
    """
    Move the source file to BACKUP_DIR with a date suffix.
    For rolling retention, only moves records older than 7 days.
    Optionally recreate the file with headers.
    FIXED: Robust timestamp parsing for mixed CSV formats.
    """
    if not os.path.exists(src):
        return

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    base = os.path.basename(src)
    name, ext = os.path.splitext(base)
    subdir = f"{name}_backup"
    dst_dir = os.path.join(BACKUP_DIR, subdir)
    os.makedirs(dst_dir, exist_ok=True)

    dst = os.path.join(dst_dir, f"{name}_{date_str}{ext}")

    if rolling and ext == '.csv':
        try:
            logger.info(f"Processing rolling retention for {src}")
            
            # Read CSV with pandas
            df = pd.read_csv(src)
            
            if df.empty:
                logger.info(f"CSV file {src} is empty, skipping rolling retention")
                return
            
            # FIXED: Use robust timestamp parsing
            logger.info(f"Parsing {len(df)} timestamps with mixed format support")
            df['timestamp'] = df['timestamp'].apply(safe_timestamp_parse)
            
            # Remove rows with invalid timestamps
            original_count = len(df)
            df = df.dropna(subset=['timestamp'])
            if len(df) < original_count:
                logger.warning(f"Dropped {original_count - len(df)} rows with invalid timestamps")
            
            if df.empty:
                logger.warning(f"No valid timestamps found in {src}, keeping file as-is")
                return
            
            # Split into recent and old data
            cutoff = datetime.utcnow() - timedelta(days=7)
            recent = df[df['timestamp'] > cutoff]
            old = df[df['timestamp'] <= cutoff]

            logger.info(f"Split data: {len(recent)} recent records, {len(old)} old records")

            # Save old data to backup
            if not old.empty:
                old.to_csv(dst, index=False)
                logger.info(f"Moved {len(old)} old records to {dst}")
            else:
                logger.info("No old records to archive")

            # Keep recent data in original file
            if not recent.empty:
                recent.to_csv(src, index=False)
                logger.info(f"Retained {len(recent)} recent records in {src}")
            else:
                # If no recent data, create file with just headers
                if headers and isinstance(headers, list):
                    with open(src, "w", encoding="utf-8") as f:
                        f.write(",".join(headers) + "\n")
                    logger.info(f"No recent records, created {src} with headers only")
                else:
                    logger.warning(f"No recent records and no headers provided for {src}")
            
            return
            
        except Exception as e:
            logger.error(f"Failed to process rolling retention for {src}: {e}")
            logger.info(f"Falling back to standard file rotation for {src}")
            # Fall through to standard rotation

    # Standard file rotation
    try:
        shutil.move(src, dst)
        logger.info(f"Moved {src} → {dst}")
    except Exception as e:
        logger.error(f"Failed to move {src}: {e}")
        return

    # Recreate file with headers if needed
    if headers:
        try:
            with open(src, "w", encoding="utf-8") as f:
                if isinstance(headers, list):
                    f.write(",".join(headers) + "\n")
                else:
                    f.write(headers + "\n")
            logger.info(f"Recreated {src} with headers")
        except Exception as e:
            logger.error(f"Could not recreate {src}: {e}")

def clear_xrp_flag():
    """
    Clear the XRP flag file if it exists.
    Used to reset XRP tweet tracking between rotations.
    """
    flag_file = os.path.join(DATA_DIR, ".xrp_tweeted")
    if os.path.exists(flag_file):
        try:
            os.remove(flag_file)
            logger.info("Cleared XRP tweet flag")
        except Exception as e:
            logger.error(f"Failed to clear XRP flag: {e}")

def rotate_logs():
    """
    Perform weekly rotation of logs and rolling retention for headlines.
    ENHANCED: Better error handling and logging throughout the process.
    """
    logger.info("Starting log rotation...")

    try:
        # Rolling retention for scored headlines with FIXED timestamp parsing
        headlines_file = os.path.join(DATA_DIR, "scored_headlines.csv")
        if os.path.exists(headlines_file):
            logger.info(f"Processing rolling retention for headlines: {headlines_file}")
            rotate_file(
                headlines_file,
                headers=["score", "headline", "url", "ticker", "timestamp"],
                rolling=True
            )
        else:
            logger.warning(f"Headlines file not found: {headlines_file}")

        # Weekly rotation for tweet log
        tweet_log_file = os.path.join(DATA_DIR, "tweet_log.csv")
        if os.path.exists(tweet_log_file):
            logger.info(f"Rotating tweet log: {tweet_log_file}")
            rotate_file(
                tweet_log_file,
                headers=["tweet_id", "timestamp", "type", "category", "text", "engagement_score"]
            )
        else:
            logger.info(f"Tweet log not found: {tweet_log_file}")

        # Rotate all log files
        rotated_count = 0
        for log_file in LOG_FILES:
            log_path = os.path.join(LOG_DIR, log_file)
            if os.path.exists(log_path):
                logger.info(f"Rotating log file: {log_file}")
                rotate_file(log_path)
                rotated_count += 1
            else:
                logger.debug(f"Log file not found: {log_file}")

        # Clear XRP flag
        clear_xrp_flag()

        logger.info(f"Log rotation complete. Rotated {rotated_count} log files.")

    except Exception as e:
        logger.error(f"Error during log rotation: {e}")
        raise

if __name__ == "__main__":
    rotate_logs()