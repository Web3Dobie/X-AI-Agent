# 🧠 Hunter X-AI Agent

Hunter is a fully autonomous AI-powered Twitter agent built to run a Web3-themed social media presence. It posts daily crypto commentary, market updates, threads, and replies — all powered by GPT-4 and real-time crypto news feeds.

## 🚀 Features

- ✅ **GPT-powered tweets**: Generates original, quote, and reply content in Hunter's distinct voice
- ✅ **Dynamic news ingestion**: Pulls headlines from CoinDesk, Decrypt, Cointelegraph, and more
- ✅ **Thread generation**: Posts 5-part market updates and 3-part opinion threads daily
- ✅ **Metrics logging**: Tracks likes, retweets, replies, and stores logs in CSV and Notion
- ✅ **Follower growth tracking**: Logs followers over time for monetization goals
- ✅ **Rate limit safe**: Built-in protection against X API limits with toggles and fallback logic
- ✅ **Verify URL and drop if 404 in "Hunter Reacts" (opinion_threads) 
- ✅ **Substack-Integration**: Weekly “Hunter Explains” threads with long-form article links (1800 - 2000 words)
- ✅ ** Rotate logs every Sunday evening and write history to D:

## 📅 Posting Schedule

- Randomise the random post times
    schedule_random_post_between(16, 18)  # Morning window
    schedule_random_post_between(18, 20)  # Midday window
    schedule_random_post_between(20, 22)  # Afternoon window

- **13:00 UTC** — Daily News Recap (3-part thread)
- **14:00 UTC** — Market Summary (5-part thread)
- **16:00 + 18:00 + 20:00 UTC** — Dynamic content (original/quote/reply)
- **18:00 + 23:00 UTC** — Replies to followers' comments
- **23:45 UTC** — GPT Opinion thread on top crypto headline (excl Friday)
- **Friday 23:00 UTC** — "Hunter Explains" thread with link to Substack and write article for Substack

- ** Sunday evening** - rotate log files to D: drive

## 🗂 Project Structure

```
/content/
    market_summary.py         # 5-token market threads
    news_recap.py             # Daily news summary thread
    opinion_thread.py         # Hunter reacts to top headline
    random_post.py            # Original, quote, or reply tweets
    explainer.py	      # Write 3 part thread on top headline of last 7 days
    explainer_writer.py	      # Write 1800 - 2000 word article for Substack
    reply_handler.py	      # Handle replies to comments and KOLs

/utils/
    gpt.py                    # GPT-4 tweet/thread generation
    x_post.py                 # All tweet/thread posting logic
    limit_guard.py            # Daily tweet limit tracker
    logger.py                 # CSV + Notion logging
    rss_fetch.py              # News ingestion via RSS
    headline_pipeline.py      # Score + store news
    post_explainer_combo.py   # Call content.opinion_thread.py and content.explainer_writer.py
    rotate_logs.py	      # Save last weeks headlines and tweets to D: and remove from .csv
    scorer.py		      # Score headlines 
    text_utils		      # Mentions and Cashtags
    notion_helpers.py         # Substack post logging to Notion DB
    notion_logger.py          # Tweet and Headline logging to Notion DB

scheduler.py                  # Main execution scheduler
README.md
.gitignore
clean_headline_log.py		# manual clean-up of headline log in case of problem
import_x_metrics.py		# manual download X analytics and parse file
```

## 📦 Dependencies

- `openai`
- `tweepy`
- `python-dotenv`
- `notion-client`
- `pandas`, `schedule`, `feedparser`

## 🔐 Secrets & API Keys

Create a `.env` file with:
```
OPENAI_API_KEY=...
X_API_KEY=...
X_API_KEY_SECRET=...
X_ACCESS_TOKEN=...
X_ACCESS_TOKEN_SECRET=...
X_USERNAME=Web3_Dobie
NOTION_TOKEN=...
TWEET_LOG_DB=...
```

## 🧠 Voice & Personality

Hunter is a snarky, loyal, crypto-native Doberman with a Web3 sixth sense.
All content is signed:
```
— Hunter 🐾
```

## ✅ Status

🟢 Fully operational.  
🐾 Let the dog tweet.

---

Made with 🧠 by AI, trained by a human, and voiced by Hunter.