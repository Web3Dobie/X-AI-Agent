"""
GPT utility module for generating tweets, threads, and longer text.
Logs errors to a centralized log file.
"""

import logging
import os

from dotenv import load_dotenv
from openai import OpenAI

from .config import LOG_DIR

# Load environment variables
load_dotenv()

# Configure logging
log_file = os.path.join(LOG_DIR, "gpt.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

client = OpenAI()


def generate_gpt_tweet(prompt: str, temperature: float = 0.9) -> str:
    """
    Generate a single tweet using GPT.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are Hunter, a crypto-native Doberman. Write bold, witty, Web3-savvy tweets. Sign off with '— Hunter 🐾'.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=280,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Error generating GPT tweet: {e}")
        return ""


def generate_gpt_thread(
    prompt: str, max_parts: int = 5, delimiter: str = "---", max_tokens: int = 1500
) -> list[str]:
    """
    Generate a multi-part thread for X via GPT.
    """
    try:
        system_prompt = (
            f"You are Hunter, a witty, crypto-savvy Doberman. "
            f"Write exactly {max_parts} tweet-length blurbs separated by '{delimiter}'. "
            "Do NOT number the tweets. End each with '— Hunter 🐾'."
        )
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.85,
        )
        raw = response.choices[0].message.content.strip()
        parts = raw.split(delimiter)
        if len(parts) < max_parts:
            parts = raw.split("\n\n")
        return [p.strip() for p in parts if p.strip()][:max_parts]
    except Exception as e:
        logging.error(f"Error generating GPT thread: {e}")
        return []


def generate_gpt_text(prompt: str, max_tokens: int = 1800, model: str = "gpt-4") -> str:
    """
    Generate longer form text (e.g., Substack article) using GPT.
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.9,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Error generating GPT text: {e}")
        return ""
