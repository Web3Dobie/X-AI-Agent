import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_unique_gpt_tweet(prompt):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are Hunter, a witty and crypto-native Doberman. Write in a bold, memorable tone and sign tweets with '— Hunter 🐾'."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=60,
        temperature=0.9
    )
    tweet = response.choices[0].message.content.strip()
    logging.info(f"🤖 Generated tweet: {tweet}")
    return tweet

def generate_news_thread():
    prompt = "Generate a 3-tweet thread summarizing today's major crypto news."
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are Hunter, a crypto-savvy Doberman summarizing the day’s top crypto headlines in threads. Use a sharp, Web3-native tone and sign each tweet with '— Hunter 🐾'."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.85
    )
    thread = response.choices[0].message.content.strip().split("\n")
    logging.info("🧵 Generated summary thread.")
    return [tweet.strip() for tweet in thread if tweet.strip()]

def generate_top_news_opinion():
    prompt = "Pick today's most impactful crypto headline and write a 2-3 tweet opinionated commentary."
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are Hunter, a sassy, sharp crypto commentator. Provide strong opinions with style, and sign tweets '— Hunter 🐾'."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=450,
        temperature=0.9
    )
    thread = response.choices[0].message.content.strip().split("\n")
    logging.info("🗞️ Generated top news opinion thread.")
    return [tweet.strip() for tweet in thread if tweet.strip()]

def generate_market_summary_thread():
    prompt = "Create a 3-part thread summarizing today's cryptocurrency market highlights and trends."
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are Hunter, a meme-literate crypto Doberman. Summarize daily market action with humor and emojis. End each tweet with '— HUnter 🐾'."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.85
    )
    thread = response.choices[0].message.content.strip().split("\n")
    logging.info("📈 Generated market summary thread.")
    return [tweet.strip() for tweet in thread if tweet.strip()]