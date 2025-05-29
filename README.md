# XAIAgent

Automated crypto news & analysis bot that fetches headlines, scores them with GPT, generates tweet threads and Substack posts, and schedules everything via a simple scheduler.

---

## 📁 Repository Structure

```
XAIAgent/
├── .env                   # environment variables (API keys, credentials)
├── README.md              # this file
├── requirements.txt       # Python dependencies
├── scheduler.py           # job scheduler entry point
├── content/               # high-level “orchestrator” scripts
│   ├── __init__.py
│   ├── headline_pipeline.py
│   ├── market_summary.py
│   ├── news_recap.py
│   ├── explainer.py
│   ├── explainer_writer.py
│   ├── opinion_thread.py
│   ├── random_post.py
│   ├── reply_handler.py
│   ├── ta_poster.py
│   ├── ta_substack_generator.py
│   ├── ta_thread_generator.py
│   └── top_news_or_explainer.py
└── utils/                 # reusable helper modules
    ├── __init__.py        # unified public API for all helpers
    ├── charts.py
    ├── config.py
    ├── email_sender.py
    ├── generate_btc_technical_charts.py
    ├── gpt.py
    ├── headline_pipeline.py
    ├── limit_guard.py
    ├── logger.py
    ├── notion_helpers.py
    ├── notion_logger.py
    ├── post_explainer_combo.py
    ├── post_ta_weekly_combo.py
    ├── publisher.py
    ├── rotate_logs.py
    ├── rss_fetch.py
    ├── scorer.py
    ├── substack_client.py
    ├── text_utils.py
    ├── x_post.py
    └── … (other helpers)
```

---

## 🔧 Installation

1. **Clone** the repo:
   ```bash
   git clone https://github.com/your-org/XAIAgent.git
   cd XAIAgent
   ```

2. **Create & activate** a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate      # macOS/Linux
   .\.venv\Scripts\activate.ps1   # Windows PowerShell
   ```

3. **Install** dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## ⚙️ Configuration

1. Copy `.env.example` to `.env` and fill in your API keys and credentials:
   ```
   OPENAI_API_KEY=…
   NOTION_TOKEN=…
   SUBSTACK_EMAIL=…
   SUBSTACK_API_KEY=…
   TWITTER_BEARER_TOKEN=…
   BOT_USER_ID=…
   ```
2. (Optional) Adjust paths or parameters in `utils/config.py`.

---

## 🚀 Usage

### 1. Running Individual Scripts

- **Fetch & score headlines**  
  ```bash
  python content/headline_pipeline.py
  ```
- **Post market summary to Substack & X**  
  ```bash
  python content/market_summary.py
  ```
- **Generate & post news recap thread**  
  ```bash
  python content/news_recap.py
  ```
- **Post “Hunter Explains” thread**  
  ```bash
  python content/explainer.py <SUBSTACK_URL>
  ```
- **Post random crypto tweet**  
  ```bash
  python content/random_post.py
  ```
- **Post weekly TA substack & thread**  
  ```bash
  python content/ta_substack_generator.py
  python content/ta_thread_generator.py [btc|eth|sol|xrp|doge]
  python content/ta_poster.py
  ```

### 2. Scheduler

All jobs (headline ingestion, market summary, explainer threads, TA threads, log rotation, etc.) are orchestrated in `scheduler.py`. Simply run:

```bash
python scheduler.py
```

The scheduler will keep running, executing each job at its configured time. You can customize schedules directly in `scheduler.py`.

---

## 🛠️ Utilities API

All low-level helpers live in `utils/` and are exposed via a single unified namespace:

```python
from utils import (
    fetch_headlines,
    score_headline,
    generate_gpt_thread,
    post_thread,
    post_to_substack_via_email,
    SubstackClient,
    write_headlines,
    clear_charts,
    generate_charts,
    fetch_binance_ohlcv,
    rotate_logs,
    log_tweet,
    has_reached_daily_limit,
    insert_cashtags,
    insert_mentions,
    # …more as needed
)
```

- **`utils/rss_fetch.py`** → `fetch_headlines(limit)`  
- **`utils/scorer.py`** → `score_headline(text)`, `score_headlines(list)`, `write_headlines(list)`  
- **`utils/gpt.py`** → `generate_gpt_tweet()`, `generate_gpt_thread()`  
- **`utils/x_post.py`** → `post_tweet()`, `post_thread()`, `post_quote_tweet()`  
- **`utils/email_sender.py`** → `post_to_substack_via_email()`  
- **`utils/substack_client.py`** → `SubstackClient`  
- **…and more.**

---

## 🧪 Linting & Testing

- **Formatting**:  
  ```bash
  black .
  isort .
  ```
- **Lint**:  
  ```bash
  flake8 .
  ```
- **(Optional) Type-check**:  
  ```bash
  mypy .
  ```

---

## 🙌 Contributing

1. Fork the repo & create a feature branch.  
2. Write code, add tests if needed.  
3. Run lint & tests locally.  
4. Submit a pull request.

---

## 📜 License

MIT © Your Name / Your Organization
