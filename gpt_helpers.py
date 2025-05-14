
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
            {"role": "system", "content": "You generate engaging, viral-worthy crypto tweets."},
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
            {"role": "system", "content": "You summarize daily crypto news clearly and engagingly in tweet threads."},
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
            {"role": "system", "content": "You provide sharp, insightful opinions on top crypto news."},
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
            {"role": "system", "content": "You summarize crypto market movements concisely and engagingly."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.85
    )
    thread = response.choices[0].message.content.strip().split("\n")
    logging.info("📈 Generated market summary thread.")
    return [tweet.strip() for tweet in thread if tweet.strip()]
