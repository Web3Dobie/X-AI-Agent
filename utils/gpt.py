"""
GPT utility module for generating tweets, threads, and longer text.
Compatible with OpenAI SDK >=1.0.0 (Azure).
Process-safe version with isolated clients.
"""

import logging
import os
from typing import List
from dotenv import load_dotenv
from openai import AzureOpenAI
from utils.config import (
    LOG_DIR,
    AZURE_OPENAI_API_KEY,
    AZURE_DEPLOYMENT_ID,
    AZURE_API_VERSION,
    AZURE_RESOURCE_NAME,
)

# Load env
load_dotenv()

# Configure logging
log_file = os.path.join(LOG_DIR, "gpt.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# --- Removed global client initialization ---
# The global client was the source of the cross-process conflict.

def _get_azure_openai_client():
    """
    Creates and returns a new, process-safe AzureOpenAI client instance.
    This function is called by each generation function to ensure resource isolation.
    """
    return AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_API_VERSION,
        azure_endpoint=f"https://{AZURE_RESOURCE_NAME}.cognitiveservices.azure.com/",
    )

def generate_gpt_tweet(prompt: str, temperature: float = 0.9) -> str:
    """Generate a single tweet using GPT."""
    try:
        # Create a fresh client for this specific request
        client = _get_azure_openai_client()
        
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_ID,
            messages=[
                {
                    "role": "system",
                    "content": "You are Hunter, a crypto-native Doberman. Write bold, witty, Web3-savvy tweets. Sign off with '— Hunter 🐾.'"
                },
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=280,
            top_p=1.0,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"Error generating GPT tweet: {e}")
        return "⚠️ Could not generate response."


def generate_gpt_thread(
    prompt: str, max_parts: int = 5, delimiter: str = "---", max_tokens: int = 1500
) -> List[str]:
    """Generate a multi-part thread for X using GPT."""
    try:
        # Create a fresh client for this specific request
        client = _get_azure_openai_client()

        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_ID,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are Hunter, a witty, crypto-savvy Doberman. "
                        f"Write exactly {max_parts} tweet-length blurbs separated by \"{delimiter}\". "
                        f"Do NOT number the tweets. End each with '— Hunter 🐾.'"
                    ),
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.85,
            max_tokens=max_tokens,
            top_p=1.0,
        )
        content = response.choices[0].message.content.strip()
        parts = content.split(delimiter)
        if len(parts) < max_parts:
            parts = content.split("\n\n")
        return [p.strip() for p in parts if p.strip()][:max_parts]

    except Exception as e:
        logging.error(f"Error generating GPT thread: {e}")
        return []


def generate_gpt_text(prompt: str, max_tokens: int = 1800) -> str:
    """Generate longer form text (e.g., Substack article) using GPT."""
    try:
        # Create a fresh client for this specific request
        client = _get_azure_openai_client()
        
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_ID,
            messages=[
                {
                    "role": "system",
                    "content": "You are Hunter, a crypto-native Doberman. Write engaging, informative articles on crypto topics."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=max_tokens,
            top_p=1.0,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"Error generating GPT text: {e}")
        return "Unable to produce Substack article at this time. Please try again later."