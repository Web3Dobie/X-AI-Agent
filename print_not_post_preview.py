from content.news_recap import generate_summary_thread
from utils.text_utils import insert_cashtags, insert_mentions


def preview_news_thread():
    thread_parts = generate_summary_thread()
    if thread_parts:
        thread_parts = [insert_cashtags(part) for part in thread_parts]
        thread_parts = [insert_mentions(part) for part in thread_parts]
        print("\n🧵 Daily Dobie Headlines (Preview):\n")
        for part in thread_parts:
            print(part)
            print("\n---")
    else:
        print("⚠️ No thread generated.")
