# Web3 Dobie X Agent

This project is a fully autonomous AI agent that runs a Twitter account focused on crypto/Web3 content. It generates posts, replies, and threads, monitors engagement, and logs metrics to CSV and Notion.

---

### 🔒 Free X API Limitations
- 500 posts / month
- 100 reads / month (very limited!)
- KOL replies require reads → disabled for now

## Features

- **Daily Posting Schedule**
  - 08:00 — Daily Dobie News Recap
  - 09:00 — Market Summary Thread (BTC, ETH, SOL, XRP, OP)
  - 10:00 — Original/Quote/comment reply (randomized)
  - 13:00 — Replies to Dobie's mentions/comments
  - # 14:00 — Reply to key opinion leaders (KOLs) until we have paid X API
  - 18:00 — Replies to Dobie's mentions/comments
  - 20:00 — Top-ranked headline opinion thread

- **Headline Ingestion + Scoring**
  - Pulls RSS feeds from CoinTelegraph, Decrypt, CryptoSlate, and others
  - Scores headlines using GPT based on novelty, clarity, and emotional pull
  - Stores to `scored_headlines.csv`

- **GPT-Generated Content**
  - Threads (news, market, opinion)
  - Quotes and originals
  - Replies to tweets or KOLs

- **Logging**
  - Tweets to `tweet_log.csv`
  - Followers to `follower_log.csv`
  - Engagement metrics to `performance_log.csv`

- **Dashboard**
  - Built with Streamlit (`dobie_dashboard.py`)
  - Visualizes tweet volume, top tweets, follower growth

---

## Setup Instructions

### 1. Clone the Repo

Unzip the archive and `cd` into the project folder.

### 2. Environment

Install dependencies using `pip` or `conda`:

```bash
pip install -r requirements.txt
```

Recommended packages:
- `openai`
- `tweepy`
- `python-dotenv`
- `feedparser`
- `streamlit`

### 3. Configure .env

Edit the `.env` file with your own credentials:

```
OPENAI_API_KEY=...
BEARER_TOKEN=...
API_KEY=...
API_SECRET=...
ACCESS_TOKEN=...
ACCESS_TOKEN_SECRET=...
BOT_USER_ID=...
```

### 4. Start the Agent

Run the scheduler:

```bash
python scheduler.py
```

To run individual functions for testing:

```bash
python run_news_thread.py
python test_all_functions.py
```

To launch the dashboard:

```bash
streamlit run dobie_dashboard.py
```

---

## Structure Overview

- `scheduler.py` — master scheduler
- `content_engine.py` — randomized tweet selector
- `post_utils.py` — all post and reply functions
- `news_fetcher.py` — RSS ingestion
- `headline_manager.py` — GPT scoring
- `news_poster.py`, `market_threader.py`, `news_threader.py` — GPT thread logic
- `metrics_logger.py`, `log_follower_count.py` — CSV logging
- `notion_logger.py`, `poster.py` — integration with Notion
- `dobie_dashboard.py` — Streamlit frontend

---

## Credits

Built by [your name]. Inspired by the idea that a Doberman can outpost half of Crypto Twitter.

For questions, reach out at [your Twitter handle].#   X - A I - A g e n t 
 
 