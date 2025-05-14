import random
import logging
from post_utils import post_original_tweet, post_quote_tweet, post_reply_to_kol

def post_random_content():
    options = [
        (post_original_tweet, 0.5),
        (post_quote_tweet, 0.25),
        (post_reply_to_kol, 0.25)
    ]
    funcs, weights = zip(*options)
    func = random.choices(funcs, weights=weights, k=1)[0]
    logging.info(f"🌀 post_random_content selected: {func.__name__}")
    func()