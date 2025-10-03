# jobs/maintenance.py

import logging
import os
import shutil
from datetime import datetime

from services.database_service import DatabaseService
from utils.config import LOG_DIR, BACKUP_DIR

logger = logging.getLogger(__name__)

def _rotate_log_file(log_name: str):
    """A simple helper to move a log file to a dated backup folder."""
    src_path = os.path.join(LOG_DIR, log_name)
    if not os.path.exists(src_path):
        return

    try:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        backup_subdir = os.path.join(BACKUP_DIR, f"{log_name}_backup")
        os.makedirs(backup_subdir, exist_ok=True)
        
        dst_path = os.path.join(backup_subdir, f"{log_name}.{date_str}")
        shutil.move(src_path, dst_path)
        logger.info(f"Rotated log file: {log_name} -> {dst_path}")
    except Exception as e:
        logger.error(f"Failed to rotate log file {log_name}: {e}")


def run_weekly_maintenance_job():
    """
    Performs weekly maintenance: database cleanup and application log rotation.
    This replaces the old rotate_logs.py script.
    """
    logger.info("🛠️ Starting Weekly Maintenance Job...")
    db_service = DatabaseService()

    try:
        # 1. Purge old records from the database
        logger.info("--- Purging old database records ---")
        # Keep the last 30 days of headlines and content logs. Adjust as needed.
        db_service.purge_old_records(table_name='headlines', days_to_keep=30)
        db_service.purge_old_records(table_name='content_log', days_to_keep=90)
        db_service.purge_old_records(table_name='ta_data', days_to_keep=365) # Keep TA data for a year
        
        # 2. Rotate application log files
        # The old CSV and flag file logic is no longer needed.
        logger.info("--- Rotating application log files ---")
        
        # Define the list of log files that are STILL IN USE
        current_log_files = [
            "scheduler.log",
            "x_post_http.log",
            "ai_service.log", # Assuming your AI service has its own log
        ]
        
        for log_file in current_log_files:
            _rotate_log_file(log_file)

        logger.info("✅ Weekly Maintenance Job completed successfully.")

    except Exception as e:
        logger.error(f"❌ Failed to complete weekly maintenance job: {e}", exc_info=True)
        raise