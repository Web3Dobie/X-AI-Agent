import os
import shutil
from datetime import datetime

# Use your specified external path
BACKUP_DIR = "D:/X AI Agent/History"
os.makedirs(BACKUP_DIR, exist_ok=True)

def rotate_file(src, headers=None):
    if not os.path.exists(src):
        return

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    base = os.path.basename(src)
    name, ext = os.path.splitext(base)
    dst = os.path.join(BACKUP_DIR, f"{name}_{date_str}{ext}")

    try:
        shutil.move(src, dst)
        print(f"📁 Moved {src} → {dst}")
    except Exception as e:
        print(f"❌ Failed to move {src}: {e}")
        return

    if headers:
        try:
            with open(src, "w", encoding="utf-8") as f:
                f.write(headers + "\n")
            print(f"🆕 Recreated {src} with headers.")
        except Exception as e:
            print(f"⚠️ Could not recreate {src}: {e}")

def rotate_logs():
    print("🔄 Rotating weekly logs...")

    rotate_file("data/scored_headlines.csv", headers="score,headline,url,ticker,timestamp")
    rotate_file("data/tweet_log.csv", headers="tweet_id,date,type,url,likes,retweets,replies,engagement_score")
    rotate_file("logs/activity.log")  # No headers needed

    print("✅ Weekly log rotation complete.")

if __name__ == "__main__":
    rotate_logs()
