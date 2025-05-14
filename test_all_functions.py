# from headline_manager import ingest_and_score_headlines, get_top_headline
# from news_threader import post_top_news_thread
from coingecko_client import get_top_tokens_data
from market_threader import generate_market_thread, post_market_summary_thread

# print("🧪 Testing: ingest_and_score_headlines()")
# ingest_and_score_headlines()
# print("✅ Headline ingestion complete.")

# print("\n🧪 Testing: get_top_headline()")
# headline, url, ticker = get_top_headline()
# print(f"✅ Top headline: {headline} — {url} — {ticker}")

# print("\n🧪 Testing: post_top_news_thread()")
# try:
#    post_top_news_thread()
#    print("✅ Top news thread posted.")
# except Exception as e:
#    print(f"❌ Failed to post news thread: {e}")

print("\n🧪 Testing: get_top_tokens_data()")
tokens = get_top_tokens_data()
for t in tokens:
    print(f"✅ ${t['symbol']}: ${t['price']:.2f} ({t['change']:+.2f}%)")

print("\n🧪 Testing: generate_market_thread()")
thread_parts = generate_market_thread()
for i, part in enumerate(thread_parts, 1):
    print(f"{i}. {part}")

print("\n🧪 Testing: post_market_summary_thread()")
try:
    post_market_summary_thread()
    print("✅ Market summary thread posted.")
except Exception as e:
    print(f"❌ Failed to post market thread: {e}")