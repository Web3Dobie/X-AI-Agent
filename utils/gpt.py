"""
GPT utility module for generating tweets, threads, and longer text.
Logs errors to a centralized log file.
"""

import logging
import os
import requests
import json

from dotenv import load_dotenv
from openai import OpenAI

from .config import LOG_DIR

from utils.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_DEPLOYMENT_ID,
    AZURE_API_VERSION,
    AZURE_RESOURCE_NAME
)

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

# client = OpenAI()

def generate_gpt_tweet(prompt: str, temperature: float = 0.9) -> str:
    """ Calls Azure OpenAI API to generate GPT-based response """
    url = f"https://{AZURE_RESOURCE_NAME}.openai.azure.com/openai/deployments/{AZURE_DEPLOYMENT_ID}/chat/completions?api-version={AZURE_API_VERSION}"   
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_API_KEY,
    }
    """ Generate a single tweet using GPT."""
    payload = {
        "messages": [
            {"role": "system", "content": "You are Hunter, a crypto-native Doberman. Write bold, witty, Web3-savvy tweets. Sign off with '— Hunter 🐾.'"},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": 280,
        "top_p": 1.0, 
    }
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload)
        response.raise_for_status()  # Raise an error for bad responses
        result = response.json()
        return result['choices'][0]['message']['content'].strip()

    except Exception as e:
        logging.error(f"Error generating GPT tweet: {e}")
        return "⚠️ Could not generate response."
    
def generate_gpt_thread(
    prompt: str, max_parts: int = 5, delimiter: str = "---", max_tokens: int = 1500
) -> list[str]:
    """
    Generate a multi-part thread for X using Azure OpenAI.
    """
    # Sanitize prompt for Azure compatibility
    # prompt = sanitize_prompt(prompt)

    url = f"https://{AZURE_RESOURCE_NAME}.openai.azure.com/openai/deployments/{AZURE_DEPLOYMENT_ID}/chat/completions?api-version={AZURE_API_VERSION}"   
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_API_KEY,
    }
    
    system_prompt = (
        f"You are Hunter, a witty, crypto-savvy Doberman. "
        f"Write exactly {max_parts} tweet-length blurbs separated by \"{delimiter}\". "
        f"Do NOT number the tweets. End each with '— Hunter 🐾.'"
)
    
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.85,
        "top_p": 1.0,
    }

    # temp logging for debugging
    #logging.debug(f"🟦 Final prompt:\n{prompt}")
    #logging.debug(f"🟦 Payload:\n{json.dumps(payload, indent=2, ensure_ascii=False)}")
 

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload
    )

        response.raise_for_status()  # Raise an error for bad responses
        content = response.json()["choices"][0]["message"]["content"].strip()
        
        parts = content.split(delimiter)
        if len(parts) < max_parts:
            parts = content.split("\n\n")
        return [p.strip() for p in parts if p.strip()][:max_parts]
    
    except requests.exceptions.HTTPError as e:
        logging.error(f"Error generating GPT thread: {e}")
        logging.error(f"Response content: {e.response.text if e.response else 'No response content'}")
    return []


def generate_gpt_text(prompt: str, max_tokens: int = 1800, model: str = "gpt-4") -> str:
    """
    Generate longer form text (e.g., Substack article) using Azure OpenAI.
    """

    url = f"https://{AZURE_RESOURCE_NAME}.openai.azure.com/openai/deployments/{AZURE_DEPLOYMENT_ID}/chat/completions?api-version={AZURE_API_VERSION}"   
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_API_KEY,
    }

    payload = {
        "messages": [
            {"role": "system", "content": "You are Hunter, a crypto-native Doberman. Write engaging, informative articles on crypto topics."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.9,
        "top_p": 1.0,
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an error for bad responses
        return response.json()["choices"][0]["message"]["content"].strip()

    except Exception as e:
        logging.error(f"Error generating GPT text: {e}")
        return "Unable to produce Substack article at this time. Please try again later."
