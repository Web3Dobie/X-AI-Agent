# world3_agent/bnb_token_sniffer.py

import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from utils.tg_notifier import send_telegram_message
import cloudscraper

SEEN_FILE = "data/seen_tokens_bnb.json"
BASE_URL = "https://bscscan.com/tokens"
SYMBOL_MATCH = "WAI"
NAME_MATCH = "world3"
SUPPLY_MIN = 990_000_000
SUPPLY_MAX = 1_010_000_000

if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        seen_contracts = set(json.load(f))
else:
    seen_contracts = set()

def save_seen():
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen_contracts), f)

def parse_supply(supply_str):
    # Handles "1,000,000,000 WAI" → 1000000000
    try:
        return int(supply_str.replace(",", "").split(" ")[0])
    except:
        return 0

def run_bnb_token_sniffer():
    print("🔍 Scanning BscScan for new tokens...")
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(BASE_URL, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select("table tbody tr")

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 5:
                continue

            name = cols[0].text.strip()
            link_tag = cols[0].find("a", href=True)
            link = "https://bscscan.com" + link_tag["href"] if link_tag else ""
            symbol = cols[1].text.strip()
            supply_str = cols[2].text.strip()
            contract = link.split("/")[-1]
            verified = bool(cols[0].find("i", class_="u-label--xs"))

            if contract in seen_contracts:
                continue

            if symbol.upper() != SYMBOL_MATCH:
                continue
            if NAME_MATCH not in name.lower():
                continue

            supply = parse_supply(supply_str)
            if not (SUPPLY_MIN <= supply <= SUPPLY_MAX):
                continue

            if not verified:
                continue  # Only alert on verified contracts

            # Alert and log
            seen_contracts.add(contract)
            save_seen()

            message = (
                f"*🚨 New $WAI Token on BNB*\n"
                f"*Name:* {name}\n"
                f"*Symbol:* {symbol}\n"
                f"*Supply:* {supply:,}\n"
                f"*Verified:* ✅\n"
                f"[View on BscScan]({link})"
            )
            send_telegram_message(message)
            print(f"📢 Alert sent for {name} ({contract})")

    except Exception as e:
        print(f"❌ Error during BNB token scan: {e}")
