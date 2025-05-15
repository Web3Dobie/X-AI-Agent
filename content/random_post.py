import random
import logging
from utils.gpt import generate_gpt_tweet
from utils.x_post import post_tweet, post_quote_tweet, reply_to_comments
from datetime import datetime
import os

def post_random_content():
    choice = random.choices(
        ["original", "quote", "reply"],
        weights=[0.98, 0.01, 0.01],
        k=1
    )[0]
    logging.info(f"🌀 post_random_content selected: {choice}")

    if choice == "original":
        prompt = "Write a standalone crypto tweet. It should be engaging, Web3-native, and end with '— Hunter 🐾'."
        text = generate_gpt_tweet(prompt)
        if text:
            post_tweet(text)

    elif choice == "quote":
        tweet_url = get_recent_viral_tweet()
        if tweet_url:
            prompt = f"Write a witty, insightful quote tweet to this post: {tweet_url}"
            text = generate_gpt_tweet(prompt)
            if text:
                post_quote_tweet(text, tweet_url)

    elif choice == "reply":
        bot_id = os.getenv("BOT_USER_ID")
        if bot_id:
            reply_to_comments(bot_id)

def get_recent_viral_tweet():
    # Static placeholder or rotating list for now
    return "https://x.com/coinbureau/status/1790104194723973536"