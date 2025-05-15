# 🧠 Hunter X-AI Agent

Hunter is a fully autonomous AI-powered Twitter agent built to run a Web3-themed social media presence. It posts daily crypto commentary, market updates, threads, and replies — all powered by GPT-4 and real-time crypto news feeds.

## 🚀 Features

- ✅ **GPT-powered tweets**: Generates original, quote, and reply content in Hunter's distinct voice
- ✅ **Dynamic news ingestion**: Pulls headlines from CoinDesk, Decrypt, Cointelegraph, and more
- ✅ **Thread generation**: Posts 5-part market updates and 3-part opinion threads daily
- ✅ **Metrics logging**: Tracks likes, retweets, replies, and stores logs in CSV and Notion
- ✅ **Follower growth tracking**: Logs followers over time for monetization goals
- ✅ **Rate limit safe**: Built-in protection against X API limits with toggles and fallback logic
- ✅ **Substack-ready**: Weekly “Hunter Explains” threads with optional long-form article links

## 📅 Posting Schedule

- **07:00 UTC** — Daily News Recap (3-part thread)
- **09:00 UTC** — Market Summary (5-part thread)
- **10:00 UTC** — Dynamic content (original/quote/reply)
- **13:00 + 18:00 UTC** — Replies to followers' comments
- **20:00 UTC** — GPT Opinion thread on top crypto headline
- **Friday** — "Hunter Explains" thread (optional Substack)

## 🗂 Project Structure

```
/content/
    market_summary.py         # 5-token market threads
    news_recap.py             # Daily news summary thread
    opinion_thread.py         # Hunter reacts to top headline
    random_post.py            # Original, quote, or reply tweets

/utils/
    gpt.py                    # GPT-4 tweet/thread generation
    x_post.py                 # All tweet/thread posting logic
    limit_guard.py            # Daily tweet limit tracker
    logger.py                 # CSV + Notion logging
    rss_fetch.py              # News ingestion via RSS
    headline_pipeline.py      # Score + store news

scheduler.py                 # Main execution scheduler
README.md
.gitignore
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