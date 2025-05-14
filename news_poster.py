import logging
from gpt_helpers import generate_news_thread
from tweet_limit_guard import has_reached_daily_limit

def post_news_thread():
    if has_reached_daily_limit():
        logging.warning("🚫 Daily tweet limit reached — skipping news thread.")
        return

    thread_parts = generate_summary_thread()
    if not thread_parts or len(thread_parts) == 0:
        logging.warning("⚠️ No thread parts generated.")
        return

    try:
        first = post_tweet(thread_parts[0], "Thread")
        if not first:
            return
        reply_id = first

        for p in thread_parts[1:]:
            from post_utils import client
            res = client.create_tweet(text=p, in_reply_to_tweet_id=reply_id)
            reply_id = res.data['id']
            logging.info(f"↳ Thread part: {p}")

        logging.info("🧵 Posted news thread successfully.")

    except Exception as e:
        logging.error(f"❌ Error posting news thread: {e}")

def generate_summary_thread():
    headlines = fetch_headlines(limit=5)
    summary_prompt = (
        "Summarize these crypto headlines into a witty, concise Twitter thread:\n" +
        "\n".join([f"• {h[0]}" for h in headlines[:3]]) +
        "\nKeep each tweet under 280 characters. Use emojis and crypto slang."
    )

    try:
        response = gpt_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a crypto-native content creator for Twitter."},
                {"role": "user", "content": summary_prompt}
            ],
            max_tokens=600,
            temperature=0.9
        )
        return [p.strip() for p in response.choices[0].message.content.strip().split("\n") if p.strip()]
    except Exception as e:
        logging.error(f"❌ Error generating summary thread: {e}")
        return []