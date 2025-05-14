import random
import logging
from post_utils import post_original_tweet, post_quote_tweet, post_reply_to_kol, reply_to_comments

# reply to KOL function disabled as long as we don;t have paid X API
#  (post_reply_to_kol, 0.25)
# reply to comments instead

def post_random_content():
    options = [
        (post_original_tweet, 0.5),
        (post_quote_tweet, 0.25),
        (reply_to_comments, 0.25)
    ]
    funcs, weights = zip(*options)
    func = random.choices(funcs, weights=weights, k=1)[0]
    logging.info(f"🌀 post_random_content selected: {func.__name__}")
    func()