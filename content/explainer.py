import logging
from datetime import datetime
from utils.gpt import generate_gpt_thread
from utils.x_post import post_thread
from utils.headline_pipeline import get_top_headline_last_7_days  # ✅ New import

SUBSTACK_URL = "https://web3dobie.substack.com/"  # Can be updated dynamically

def post_dobie_explainer_thread():
    logging.info("🧵 Starting Dobie explainer thread generation...")

    headline = get_top_headline_last_7_days()  # ✅ Use shared top headline logic
    if not headline:
        logging.warning("❌ No headline found for explainer thread")
        return

    topic = headline["headline"]
    url = headline["url"]
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    prompt = f"""
Write a 3-part Twitter thread called 'Hunter Explains' about:
"{topic}"

Make it simple, clever, and accessible for casual readers. Add emojis and bold takes.
Each tweet must be <280 characters and end with '— Hunter 🐾'.
End the last tweet with a call to action and this link: {url}
Start with: Hunter Explains 🧵 [{today_str}]
"""

    thread = generate_gpt_thread(prompt, max_parts=3)
    if thread:
        thread[0] = f"Hunter Explains 🧵 [{today_str}]\n" + thread[0]
        thread[-1] += f"\n{SUBSTACK_URL}"  # ✅ Include source or Substack link
        post_thread(thread, category="explainer")
        logging.info("✅ Explainer thread posted")
    else:
        logging.warning("⚠️ GPT returned no content for explainer thread")

