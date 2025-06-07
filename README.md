# XAIAgent

Automated crypto news & analysis bot that fetches headlines, scores them with GPT, generates tweet threads and Substack posts, and schedules everything via a simple scheduler.

---

## 📁 Repository Structure

XAIAgent/ 
├── .env # environment variables (API keys, credentials) 
├── README.md # this file 
├── requirements.txt # Python dependencies 
├── scheduler.py # job scheduler entry point 
├── content/ # high-level “orchestrator” scripts 
│ ├── init.py 
│ ├── headline_pipeline.py 
│ ├── market_summary.py 
│ ├── news_recap.py 
│ ├── explainer.py 
│ ├── explainer_writer.py 
│ ├── opinion_thread.py 
│ ├── random_post.py 
│ ├── reply_handler.py 
│ ├── ta_poster.py 
│ ├── ta_substack_generator.py 
│ ├── ta_thread_generator.py │
 └── top_news_or_explainer.py 
 ├── utils/ # reusable helper modules 
 │ ├── init.py 
 │ ├── charts.py 
 │ ├── config.py 
 │ ├── email_sender.py 
 │ ├── generate_btc_technical_charts.py 
 │ ├── gpt.py 
 │ ├── headline_pipeline.py 
 │ ├── limit_guard.py 
 │ ├── logger.py 
 │ ├── notion_helpers.py 
 │ ├── notion_logger.py 
 │ ├── post_explainer_combo.py 
 │ ├── post_ta_weekly_combo.py 
 │ ├── publisher.py 
 │ ├── rotate_logs.py 
 │ ├── rss_fetch.py 
 │ ├── scorer.py 
 │ ├── substack_client.py 
 │ ├── text_utils.py 
 │ ├── x_post.py 
 │ └── … (other helpers) 
 ├── ta_posts/ # generated technical analysis markdowns 
 ├── substack_posts/ # generated Substack posts 
 ├── logs/ # log files 
 ├── Notion/ # Notion toolkit & docs 
 ├── backup/ # backup files └── ... # other directories and files


---

## 🔧 Installation

1. **Clone** the repo:
   ```bash
   git clone https://github.com/your-org/XAIAgent.git
   cd XAIAgent

2. Create & activate a virtual environment:
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
.\.venv\Scripts\activate.ps1   # Windows PowerShell

3. Install dependencies:
pip install -r requirements.txt

⚙️ Configuration
1. Copy .env.example to .env and fill in your API keys and credentials:
OPENAI_API_KEY=…
NOTION_TOKEN=…
SUBSTACK_EMAIL=…
SUBSTACK_API_KEY=…
TWITTER_BEARER_TOKEN=…
BOT_USER_ID=…

2. (Optional) Adjust paths or<vscode_annotation details='%5B%7B%22title%22%3A%22hardcoded-credentials%22%2C%22description%22%3A%22Embedding%20credentials%20in%20source%20code%20risks%20unauthorized%20access%22%7D%5D'> parameters</vscode_annotation> in utils/config.py.

🚀 Usage
1. Running Individual Scripts
Fetch & score headlines
Post market summary to Substack & X
Generate & post news recap thread
Post “Hunter Explains” thread
Post random crypto tweet
Post weekly TA substack & thread

2. Scheduler
All jobs (headline ingestion, market summary, explainer threads, TA threads, log rotation, etc.) are orchestrated in scheduler.py. Simply run:
python3 scheduler.py

The scheduler will keep running, executing each job at its configured time. You can customize schedules directly in scheduler.py.

🛠️ Utilities API
All low-level helpers live in utils/ and are exposed via a single unified namespace:

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

utils/rss_fetch.py → fetch_headlines(limit)
utils/scorer.py → score_headline(text), score_headlines(list), write_headlines(list)
utils/gpt.py → generate_gpt_tweet(), generate_gpt_thread()
utils/x_post.py → post_tweet(), post_thread(), post_quote_tweet()
utils/email_sender.py → post_to_substack_via_email()
utils/substack_client.py → SubstackClient
…and more.

🧪 Linting & Testing
Formatting:
black .
isort .

Lint:
flake8 .

(Optional) Type-check:
mypy .

🙌 Contributing
Fork the repo & create a feature branch.
Write code, add tests if needed.
Run lint & tests locally.
Submit a pull request.
📜 License
MIT © DutchBrat / Web3Dobie ```