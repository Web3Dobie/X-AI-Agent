import os
import csv
import logging
from utils.notion_logger import log_headline
import re
import math
from datetime import datetime
from utils.gpt import client
from dotenv import load_dotenv

load_dotenv()

HEADLINE_LOG = "data/scored_headlines.csv"

def extract_ticker(headline):
    for word in headline.split():
        if word.startswith("$") and len(word) <= 6:
            return word.upper().replace("$", "")
    return "CRYPTO"

def score_headlines(headlines):
    scored = []
    now = datetime.utcnow().isoformat()

    for h in headlines:
        # Safety check: ensure h is a dict and has required fields
        if not isinstance(h, dict) or "headline" not in h or "url" not in h:
            logging.warning(f"❌ Skipping non-dict or incomplete headline input: {h}")
            continue

        prompt = f"Score this crypto news headline from 1 to 10 based on how likely it is to go viral on Twitter: '{h['headline']}'"
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a Twitter algorithm expert. Score crypto headlines for viral potential."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                temperature=0.3
            )

            score_str = response.choices[0].message.content.strip()
            match = re.search(r"\b\d+(\.\d+)?\b", score_str)

            if not match:
                logging.warning(f"⚠️ GPT returned unparseable score: {score_str}")
                continue

            try:
                score = math.ceil(float(match.group()))
            except Exception as e:
                logging.warning(f"⚠️ Failed to convert score to float: {score_str} — {e}")
                continue

            ticker = extract_ticker(h["headline"])

            # ✅ Construct a clean dict with only expected fields
            cleaned = {
                "headline": h["headline"],
                "url": h["url"],
                "score": score,
                "ticker": ticker,
                "timestamp": now
            }
            scored.append(cleaned)

        except Exception as e:
            logging.warning(f"⚠️ Failed to score headline: {h.get('headline', str(h))} — {e}")

    if scored:
        write_headlines(scored)
        return  # Removed return of full scored list to prevent CSV corruption


def write_headlines(scored):
    os.makedirs("data", exist_ok=True)
    exists = os.path.exists(HEADLINE_LOG)

    with open(HEADLINE_LOG, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=["score", "headline", "url", "ticker", "timestamp"])
        if not exists:
            writer.writeheader()

        for h in scored:
            try:
                # Validate all fields before writing
                if not all(k in h for k in ["score", "headline", "url", "ticker", "timestamp"]):
                    raise ValueError("Missing one or more required keys")

                # Validate score is numeric
                score = float(h["score"])

                # Write clean row
                writer.writerow({
                    "score": score,
                    "headline": h["headline"],
                    "url": h["url"],
                    "ticker": h["ticker"],
                    "timestamp": h["timestamp"]
                })

                log_headline(
                    date_ingested=h["timestamp"],
                    headline=h["headline"],
                    relevance_score=score,
                    viral_score=score,
                    used=False,
                    source_url=h["url"]
                )

            except Exception as e:
                logging.warning(f"⚠️ Skipped malformed headline before writing: {h} — {e}")
     
    logging.info(f"✅ Successfully wrote {len(scored)} headlines to log.")

