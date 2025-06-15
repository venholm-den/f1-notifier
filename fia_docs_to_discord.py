# fia_docs_to_discord.py

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, UTC
import os
import time
import hashlib
import requests

FIA_DOCS_URL = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season/season-2025-2071"
WEBHOOK_URL = os.getenv("F1_DOCS_WEBHOOK")
LAST_HASH_FILE = "last_fia_doc_hash.txt"
USE_YESTERDAY = True  # Set to False if you want today's documents

def get_docs_by_date():
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(options=options)

    try:
        print("🚀 Launching Firefox with Selenium...")
        driver.get(FIA_DOCS_URL)
        time.sleep(6)  # Let JS load everything
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Save the page source for debugging
        with open("fia_page_dump.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

        table = soup.find("table", class_="views-table")
        if not table:
            print("‼️ Could not find FIA document table.")
            return []

        target_date = datetime.now(UTC) - timedelta(days=1) if USE_YESTERDAY else datetime.now(UTC)
        date_str = target_date.strftime("%d.%m.%Y")
        print(f"🔍 Looking for FIA documents from: {date_str}")

        docs = []
        for row in table.select("tbody tr"):
            cols = row.find_all("td")
            if len(cols) < 2:
                continue

            published = cols[-1].text.strip()
            if published != date_str:
                continue

            title = cols[0].text.strip()
            link_tag = cols[0].find("a")
            if not link_tag or not link_tag.get("href"):
                continue

            link = "https://www.fia.com" + link_tag["href"]
            docs.append({"title": title, "link": link, "published": published})

        return docs

    finally:
        driver.quit()

def compute_doc_hash(doc):
    return hashlib.sha256((doc["title"] + doc["link"]).encode()).hexdigest()

def load_last_hash():
    if not os.path.exists(LAST_HASH_FILE):
        return None
    with open(LAST_HASH_FILE, "r") as f:
        return f.read().strip()

def save_last_hash(h):
    with open(LAST_HASH_FILE, "w") as f:
        f.write(h)

def post_to_discord(doc):
    if not WEBHOOK_URL:
        raise EnvironmentError("F1_DOCS_WEBHOOK is not set.")
    payload = {
        "embeds": [{
            "title": doc["title"],
            "url": doc["link"],
            "description": f"📄 Published: {doc['published']}",
            "color": 0x3498DB,
            "footer": {"text": "FIA F1 Document Update"}
        }]
    }
    res = requests.post(WEBHOOK_URL, json=payload)
    res.raise_for_status()

def main():
    docs = get_docs_by_date()
    if not docs:
        print("No documents from that date — exiting.")
        return

    last_hash = load_last_hash()
    new_hashes = []

    for doc in reversed(docs):
        doc_hash = compute_doc_hash(doc)
        new_hashes.append(doc_hash)

        if doc_hash == last_hash:
            print(f"⏭️ Skipping already-posted doc: {doc['title']}")
            continue

        print(f"📢 Posting new document: {doc['title']}")
        post_to_discord(doc)

    if new_hashes:
        save_last_hash(new_hashes[-1])

if __name__ == "__main__":
    main()
