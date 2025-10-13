# jobs/maintenance.py

import logging
import os
import shutil
from datetime import datetime

from services.database_service import DatabaseService
from utils.config import LOG_DIR, BACKUP_DIR

logger = logging.getLogger(__name__)

def _rotate_log_file(log_name: str) -> bool:
    """
    A simple helper to move a log file to a dated backup folder.
    Returns True if successful, False otherwise.
    """
    src_path = os.path.join(LOG_DIR, log_name)
    if not os.path.exists(src_path):
        logger.debug(f"Log file {log_name} does not exist, skipping rotation")
        return False

    try:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        backup_subdir = os.path.join(BACKUP_DIR, f"{log_name}_backup")
        os.makedirs(backup_subdir, exist_ok=True)
        
        dst_path = os.path.join(backup_subdir, f"{log_name}.{date_str}")
        shutil.move(src_path, dst_path)
        logger.info(f"Rotated log file: {log_name} -> {dst_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to rotate log file {log_name}: {e}")
        return False


def run_weekly_maintenance_job():
    """
    Performs weekly maintenance: database cleanup and application log rotation.
    This replaces the old rotate_logs.py script.
    """
    logger.info("🛠️ Starting Weekly Maintenance Job...")
    db_service = DatabaseService()
    
    # Track purge results for summary
    purge_results = {}

    try:
        # 1. Purge old records from the database
        logger.info("--- Purging old database records ---")
        
        # Define retention policies
        retention_policies = {
            'headlines': 30,
            'job_executions': 30,
            'content_log': 90,
            'ta_data': 365
        }
        
        # Execute purges and collect results
        for table_name, days_to_keep in retention_policies.items():
            deleted_count = db_service.purge_old_records(
                table_name=table_name, 
                days_to_keep=days_to_keep
            )
            purge_results[table_name] = {
                'deleted': deleted_count,
                'retention_days': days_to_keep
            }
        
        # 2. Rotate application log files
        logger.info("--- Rotating application log files ---")
        
        # Define the list of log files that are STILL IN USE
        current_log_files = [
            "scheduler.log",
            "x_post_http.log",
            "ai_service.log",
        ]
        
        rotated_count = 0
        for log_file in current_log_files:
            if _rotate_log_file(log_file):
                rotated_count += 1
        
        # 3. Generate summary
        total_deleted = sum(result['deleted'] for result in purge_results.values())
        
        summary = [
            "📊 Weekly Maintenance Summary:",
            f"   Database purge: {total_deleted} total records deleted"
        ]
        
        for table_name, result in purge_results.items():
            if result['deleted'] > 0:
                summary.append(
                    f"      • {table_name}: {result['deleted']} records "
                    f"(>{result['retention_days']} days old)"
                )
        
        summary.append(f"   Log rotation: {rotated_count}/{len(current_log_files)} files rotated")
        
        summary_text = "\n".join(summary)
        logger.info(summary_text)
        
        # Send Telegram notification with summary
        from utils.tg_notifier import send_telegram_message
        send_telegram_message(
            f"✅ Weekly Maintenance Complete\n\n{summary_text}",
            parse_mode=None
        )

        logger.info("✅ Weekly Maintenance Job completed successfully.")

    except Exception as e:
        error_msg = f"❌ Weekly maintenance failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Send error notification
        from utils.tg_notifier import send_telegram_message
        send_telegram_message(error_msg, parse_mode=None)
        
        raise