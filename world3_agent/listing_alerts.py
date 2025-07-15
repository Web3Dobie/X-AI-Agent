# listing_alerts.py

import feedparser
import cloudscraper
import snscrape.modules.twitter as sntwitter
import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

from utils.tg_notifier import send_telegram_message
import logging
logger = logging.getLogger("listing_alerts")

load_dotenv()

last_alerted = {}
ALERT_COOLDOWN = timedelta(hours=24)  # Cooldown period for alerts

KEYWORDS = ['wai', '$wai', 'world3', 'world3.ai']

SOURCES = {
    'binance': 'https://www.binance.com/en/support/announcement/rss',
    'okx': 'https://www.okx.com/support/hc/en-us/rss/360000030212',
    'kucoin': 'https://www.kucoin.com/news/rss',
    'coinex': 'https://announcement.coinex.com/hc/en-us/categories/360000300154.atom',
}

def keyword_match(text):
    return any(kw.lower() in text.lower() for kw in KEYWORDS)

def send_alert(source, title, link):
    now = datetime.utcnow()
    last_time = last_alerted.get(source.lower())

    if last_time and now - last_time < ALERT_COOLDOWN:
        print(f"⚠️ Skipping duplicate alert from {source} (within cooldown window)")
        return

    message = f"*{source.upper()} ALERT*\n{title}\n{link}"
    try:
        send_telegram_message(message)
        last_alerted[source.lower()] = now  # Save time
    except Exception as e:
        print(f"❌ Telegram alert failed: {e}")


def check_rss_feeds():
    for name, url in SOURCES.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            link = entry.get("link", "")
            if keyword_match(title + summary):
                send_alert(name, title, link)

def check_coinbase_blog():
    print("🔍 Checking Coinbase blog via Cloudscraper...")
    url = "https://blog.coinbase.com/"
    try:
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
        response = scraper.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        articles = soup.select("h2 > a")
        for article in articles[:5]:
            title = article.get_text(strip=True)
            link = article.get("href")
            full_link = link if link.startswith("http") else f"https://blog.coinbase.com{link}"
            if keyword_match(title):
                send_alert("Coinbase Blog", title, full_link)
    except Exception as e:
        print(f"❌ Failed to fetch Coinbase blog: {e}")

def check_gateio():
    print("🔍 Checking Gate.io announcements...")
    url = "https://www.gate.io/en/articlelist/ann"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Gate.io uses article titles inside h3 tags within anchor tags
        articles = soup.select("div.main-content .article-item h3")
        for article in articles[:5]:  # check the latest 5
            title = article.get_text(strip=True)
            link_tag = article.find_parent("a")
            link = "https://www.gate.io" + link_tag["href"] if link_tag else ""
            if keyword_match(title):
                send_alert("Gate.io", title, link)
    except Exception as e:
        print(f"❌ Failed to fetch Gate.io: {e}")

import cloudscraper

def check_mexc():
    print("🔍 Checking MEXC listings via Cloudscraper...")
    url = "https://support.mexc.com/hc/en-us/sections/360000547811-New-Listings"
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        articles = soup.select("li.article-list-item a")
        for article in articles[:5]:
            title = article.get_text(strip=True)
            link = "https://support.mexc.com" + article["href"]
            if keyword_match(title):
                send_alert("MEXC", title, link)
    except Exception as e:
        print(f"❌ Failed to fetch MEXC: {e}")

def run_listing_alerts():
    logger.info("Running Tier 1 listing scan...")
    print("📡 Checking Tier 1 listings...")
    check_rss_feeds()
    check_coinbase_blog()
    check_gateio()
    # check_mexc()
