"""
Rotate key CSVs and logs weekly by moving them into dated subfolders under BACKUP_DIR.
Handles rolling retention for scored headlines and weekly rotation for other logs.
FIXED: All print() statements replaced with proper logging.
"""

import os
import shutil
import csv
import logging
from datetime import datetime, timedelta
import pandas as pd

from .config import BACKUP_DIR, DATA_DIR, LOG_DIR

# Configure logging for this module
logger = logging.getLogger(__name__)

# Ensure backup directory exists
try:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    logger.debug(f"Backup directory ensured: {BACKUP_DIR}")
except Exception as e:
    logger.error(f"Failed to create backup directory {BACKUP_DIR}: {e}")

# List of log files to rotate weekly
LOG_FILES = [
    "gpt.log",
    "content.market_summary.log",
    "content.news_recap.log",
    "content.opinion_thread.log",
    "content.ta_poster.log",
    "utils.rss_fetch.log",
    "notion_logger.log",
    "x_post_http.log",
    "scheduler.log",  # Added scheduler log
    "application.log"  # Added application log if exists
]

def rotate_file(src, headers=None, rolling=False):
    """
    Move the source file to BACKUP_DIR with a date suffix.
    For rolling retention, only moves records older than 7 days.
    Optionally recreate the file with headers.
    """
    if not os.path.exists(src):
        logger.debug(f"File does not exist, skipping: {src}")
        return

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    base = os.path.basename(src)
    name, ext = os.path.splitext(base)
    subdir = f"{name}_backup"
    dst_dir = os.path.join(BACKUP_DIR, subdir)
    
    try:
        os.makedirs(dst_dir, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create backup subdirectory {dst_dir}: {e}")
        return

    dst = os.path.join(dst_dir, f"{name}_{date_str}{ext}")

    if rolling and ext == '.csv':
        try:
            # Read CSV with pandas
            df = pd.read_csv(src)
            
            # Check if timestamp column exists
            if 'timestamp' not in df.columns:
                logger.warning(f"No timestamp column found in {src}, performing standard rotation")
                # Fall through to standard rotation
            else:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # Split into recent and old data
                cutoff = datetime.utcnow() - timedelta(days=7)
                recent = df[df['timestamp'] > cutoff]
                old = df[df['timestamp'] <= cutoff]

                # Save old data to backup
                if not old.empty:
                    old.to_csv(dst, index=False)
                    logger.info(f"[ROLLING] Moved {len(old)} old records to {dst}")

                # Keep recent data in original file
                recent.to_csv(src, index=False)
                logger.info(f"[KEEP] Retained {len(recent)} recent records in {src}")
                return
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to process rolling retention for {src}: {e}")
            # Fall through to standard rotation as fallback

    # Standard file rotation
    try:
        shutil.move(src, dst)
        logger.info(f"[FOLDER] Moved {src} → {dst}")
    except Exception as e:
        logger.error(f"[ERROR] Failed to move {src}: {e}")
        return

    # Recreate file with headers if needed
    if headers:
        try:
            with open(src, "w", encoding="utf-8") as f:
                if isinstance(headers, list):
                    f.write(",".join(headers) + "\n")
                else:
                    f.write(headers + "\n")
            logger.info(f"[NEW] Recreated {src} with headers.")
        except Exception as e:
            logger.error(f"[ALERT] Could not recreate {src}: {e}")

def clear_xrp_flag():
    """
    Clear the XRP flag file if it exists.
    Used to reset XRP tweet tracking between rotations.
    """
    # Check both possible locations for XRP flag
    possible_flag_locations = [
        os.path.join(DATA_DIR, ".xrp_tweeted"),
        os.path.join(LOG_DIR, "xrp_used.flag"),
        os.path.join(DATA_DIR, "xrp_used.flag")
    ]
    
    for flag_file in possible_flag_locations:
        if os.path.exists(flag_file):
            try:
                os.remove(flag_file)
                logger.info(f"[FLAG] Cleared XRP tweet flag: {flag_file}")
            except Exception as e:
                logger.error(f"[ERROR] Failed to clear XRP flag {flag_file}: {e}")

def rotate_logs():
    """
    Perform weekly rotation of logs and rolling retention for headlines.
    ENHANCED: Better error handling and more comprehensive cleanup.
    """
    logger.info("Starting log rotation...")
    
    rotation_start_time = datetime.utcnow()
    files_rotated = 0
    files_failed = 0

    try:
        # Rolling retention for scored headlines
        headlines_file = os.path.join(DATA_DIR, "scored_headlines.csv")
        if os.path.exists(headlines_file):
            rotate_file(
                headlines_file,
                headers=["score", "headline", "url", "ticker", "timestamp"],
                rolling=True
            )
            files_rotated += 1
        else:
            logger.warning("scored_headlines.csv not found for rotation")

        # Weekly rotation for tweet log
        tweet_log_file = os.path.join(DATA_DIR, "tweet_log.csv")
        if os.path.exists(tweet_log_file):
            rotate_file(
                tweet_log_file,
                headers="tweet_id,timestamp,type,category,text,engagement_score"
            )
            files_rotated += 1
        else:
            logger.info("tweet_log.csv not found (this is normal for new installations)")

        # Rotate all log files
        for log_file in LOG_FILES:
            log_path = os.path.join(LOG_DIR, log_file)
            if os.path.exists(log_path):
                try:
                    rotate_file(log_path)
                    files_rotated += 1
                except Exception as e:
                    logger.error(f"Failed to rotate log file {log_file}: {e}")
                    files_failed += 1
            else:
                logger.debug(f"Log file not found: {log_file}")

        # Clear XRP flags
        clear_xrp_flag()
        
        # Clean up empty backup directories (optional maintenance)
        try:
            for item in os.listdir(BACKUP_DIR):
                item_path = os.path.join(BACKUP_DIR, item)
                if os.path.isdir(item_path) and not os.listdir(item_path):
                    os.rmdir(item_path)
                    logger.debug(f"Removed empty backup directory: {item}")
        except Exception as e:
            logger.warning(f"Failed to clean empty backup directories: {e}")

    except Exception as e:
        logger.error(f"Critical error during log rotation: {e}")
        files_failed += 1

    # Report rotation results
    rotation_duration = datetime.utcnow() - rotation_start_time
    logger.info(f"[OK] Log rotation complete. Files rotated: {files_rotated}, Failed: {files_failed}, Duration: {rotation_duration}")
    
    if files_failed > 0:
        logger.warning(f"Log rotation completed with {files_failed} failures. Check logs for details.")

if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    rotate_logs()