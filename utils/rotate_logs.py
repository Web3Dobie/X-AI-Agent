"""
Rotate key CSVs and logs weekly by moving them into dated subfolders under BACKUP_DIR.
Preserves original functions: rotate_file, rotate_logs, clear_xrp_flag.
"""

import os
import shutil
from datetime import datetime

from .config import BACKUP_DIR, DATA_DIR, LOG_DIR

# Ensure backup directory exists
os.makedirs(BACKUP_DIR, exist_ok=True)


def rotate_file(src, headers=None):
    """
    Move the source file to BACKUP_DIR with a date suffix.
    If the file is locked (e.g., activity.log), rename/truncate accordingly.
    Optionally recreate the file with headers.
    """
    if not os.path.exists(src):
        return

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    base = os.path.basename(src)
    name, ext = os.path.splitext(base)
    # Create a subdirectory per file type for organization
    subdir = f"{name}_backup"
    dst_dir = os.path.join(BACKUP_DIR, subdir)
    os.makedirs(dst_dir, exist_ok=True)

    dst = os.path.join(dst_dir, f"{name}_{date_str}{ext}")

    try:
        shutil.move(src, dst)
        print(f"[FOLDER] Moved {src} → {dst}")
    except PermissionError:
        if "activity.log" in src:
            print("[ALERT] activity.log is locked. Truncating instead.")
            try:
                with open(src, "w", encoding="utf-8"):
                    pass  # truncate
                print("Truncated activity.log.")
            except Exception as e:
                print(f"[ERROR] Failed to truncate {src}: {e}")
        else:
            print(f"[ERROR] Permission denied moving {src}")
        return
    except Exception as e:
        print(f"[ERROR] Failed to move {src}: {e}")
        return

    if headers:
        try:
            with open(src, "w", encoding="utf-8") as f:
                f.write(headers + "\n")
            print(f"[NEW] Recreated {src} with headers.")
        except Exception as e:
            print(f"[ALERT] Could not recreate {src}: {e}")


def rotate_logs():
    """
    Perform weekly rotation of key data and log files.
    """
    print("Rotating weekly logs...")

    # Rotate scored headlines CSV
    rotate_file(
        os.path.join(DATA_DIR, "scored_headlines.csv"),
        headers="timestamp,headline,url,score",
    )
    # Rotate tweet log CSV
    rotate_file(
        os.path.join(DATA_DIR, "tweet_log.csv"),
        headers="tweet_id,timestamp,type,category,text,engagement_score",
    )
    # Rotate activity log
    rotate_file(os.path.join(LOG_DIR, "activity.log"))

    print("[OK] Weekly log rotation complete.")


def clear_xrp_flag():
    """
    Remove the xrp_used.flag daily to reset the flag state.
    """
    flag_path = os.path.join(LOG_DIR, "xrp_used.flag")
    if os.path.exists(flag_path):
        os.remove(flag_path)
        print("Reset xrp_used.flag")


if __name__ == "__main__":
    rotate_logs()
