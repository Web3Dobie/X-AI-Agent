import logging
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI()

def generate_gpt_tweet(prompt, temperature=0.9):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are Hunter, a crypto-native Doberman. Write bold, witty, Web3-savvy tweets. Sign off with '— Hunter 🐾'."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=280,
            temperature=temperature
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"❌ Error generating GPT tweet: {e}")
        return ""

def generate_gpt_thread(prompt, max_parts=5, delimiter="---"):
    try:
        system_prompt = f"You are Hunter, a witty, crypto-savvy Doberman. Write exactly {max_parts} tweet-length blurbs. Separate each blurb with '{delimiter}'. Do NOT number or title the tweets. End each with '— Hunter 🐾'."
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.85
        )
        raw = response.choices[0].message.content.strip()
        parts = raw.split(delimiter)

        # fallback
        if len(parts) < max_parts:
            parts = raw.split("\n\n")

        return [p.strip() for p in parts if p.strip()][:max_parts]

    except Exception as e:
        logging.error(f"❌ Error generating GPT thread: {e}")
        return []