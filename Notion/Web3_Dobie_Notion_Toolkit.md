
# 🐶 Web3 Dobie Agent – Notion Toolkit

Welcome to your centralized Notion-style toolkit for managing and growing the Web3 Dobie Agent on X (Twitter). This workspace includes content planning, ingestion tracking, tweet metrics, system architecture, and monetization tracking.

---

## ✅ Dashboard (Quick Access)

- [Content Calendar](#calendar)
- [Headline Vault](#headline-vault)
- [Tweet Archive + Metrics](#tweet-archive--metrics)
- [Weekly Reports](#weekly-report-log)
- [Monetization Tracker](#monetization-tracker)
- [System Diagram](#agent-system-map-diagram--notes)

---

## 📅 Content Calendar

| Date | Type    | Topic                  | Status    | Link to Tweet | Notes                       |
|------|---------|------------------------|-----------|---------------|-----------------------------|
| May 13 | News    | Bitcoin ETF Rumors       | Scheduled |               | Based on Bloomberg headline |
| May 13 | Original | Market Pulse Opinion     | Draft     |               | GPT-based daily commentary  |
| May 12 | Quote   | CZ on market manipulation | Posted    | [Tweet](https://x.com/tweet/123456) | Quoted tweet with comment   |

---

## 📰 Headline Vault

| Date Ingested | Headline                                 | Relevance | Viral Score | Used | Tweet ID |
|---------------|------------------------------------------|-----------|-------------|------|----------|
| May 12 | BlackRock updates Bitcoin ETF filing | 8.9       | 9.1         | ✅    | 123456   |
| May 13 | Tether announces Bitcoin mining plans  | 7.4       | 6.8         | ❌    |          |

---

## 📊 Tweet Archive + Metrics

| Tweet ID | Date       | Type    | Likes | RTs | Replies | Engagement | URL                              |
|----------|------------|---------|-------|-----|---------|------------|----------------------------------|
| 123456   | May 12 | News    | 42    | 10  | 6       | 72.4       | https://x.com/tweet/123456       |
| 123457   | May 13     | Original| 18    | 3   | 1       | 26.5       | https://x.com/tweet/123457       |

---

## 🧠 Agent System Map (Diagram + Notes)

**Components:**
- `scheduler.py` – orchestrates daily/weekly posts
- `headline_ingestor.py` – scrapes crypto news and stores headlines
- `scoring.py` – ranks headlines on relevance and virality
- `poster.py` – posts original, quote, and news content
- `metrics_logger.py` – tracks tweet ID, engagement, impressions
- `safe_mode` toggle – prevents overposting during rate limit periods

---

## 📈 Weekly Report Log

| Week Ending | Follower Growth | Top Tweets     | Summary              |
|-------------|------------------|----------------|----------------------|
| May 11     | +28             | 123456, 123457 | Testing headline ranking, safe mode active |

---

## 💰 Monetization Tracker

| Metric               | Target | Current | Progress |
|----------------------|--------|---------|----------|
| Verified Followers   | 500    | 132     | 26.4%    |
| Monthly Impressions  | 1,000,000 | 232,000 | 23.2%    |

---

## 💡 Prompt + Ideas Vault

| Prompt                                  | Type      | Status   |
|-----------------------------------------|-----------|----------|
| "What if ETH flips BTC in 2025?"        | Thread    | Draft    |
| "Will memecoins dominate 2024 altseason?" | Opinion   | Idea     |
| "CZ: Market Manipulator or Martyr?"     | Quote     | Posted   |

---

## 📋 Task Board

| To Do                              | In Progress         | Done                           |
|-----------------------------------|----------------------|--------------------------------|
| Add Notion-based dashboard        |                      | ✅ Resume ingestion             |
| Add GPT thread generation logic   | ✅ Testing top story  |                                |
| Build Streamlit analytics view    |                      |                                |
