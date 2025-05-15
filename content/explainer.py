import logging
from datetime import datetime
from utils.gpt import generate_gpt_thread
from utils.x_post import post_thread

SUBSTACK_URL = "https://web3dobie.substack.com/"  # Can be updated dynamically

def post_dobie_explainer_thread():
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    prompt = f"""
Write a 3-part Twitter thread called 'Hunter Explains' about a hot topic in crypto or Web3 this week.

Make it simple, clever, and accessible for casual readers. Add emojis and bold takes. Each tweet must be <280 characters and end with '— Hunter 🐾'.
End the last tweet with a call to action and this link: {SUBSTACK_URL}
Start with: Hunter Explains 🧵 [YYYY-MM-DD]
"""

    thread = generate_gpt_thread(prompt, max_parts=3)
    if thread:
        thread[0] = f"Hunter Explains 🧵 [{today_str}]\n" + thread[0]
        thread[-1] += f"\n{SUBSTACK_URL}"
        post_thread(thread, category="explainer")