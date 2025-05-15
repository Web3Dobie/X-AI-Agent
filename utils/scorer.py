import os
import csv
import logging
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
            match = re.search(r"\d+(\.\d+)?", score_str)
            score = math.ceil(float(match.group())) if match else 0
            ticker = extract_ticker(h["headline"])
            h["score"] = score
            h["ticker"] = ticker
            h["timestamp"] = now
            scored.append(h)
        except Exception as e:
            logging.warning(f"⚠️ Failed to score headline: {h['headline']} — {e}")

    if scored:
        write_headlines(scored)

def write_headlines(scored):
    os.makedirs("data", exist_ok=True)
    exists = os.path.exists(HEADLINE_LOG)
    with open(HEADLINE_LOG, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=["score", "headline", "url", "ticker", "timestamp"])
        if not exists:
            writer.writeheader()
        for h in scored:
            writer.writerow({
                "score": h["score"],
                "headline": h["headline"],
                "url": h["url"],
                "ticker": h["ticker"],
                "timestamp": h["timestamp"]
            })