# fia_docs_to_discord.py

import os
import time
import hashlib
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

FIA_DOCS_URL = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season/season-2025-2071"
WEBHOOK_URL = os.getenv("F1_DOCS_WEBHOOK")
LAST_HASH_FILE = "last_fia_doc_hash.txt"

def get_page_html():
    print("🚀 Launching Firefox with Selenium...")
    options = Options()
    options.headless = True

    # Specify Firefox binary path on GitHub Actions runner
    if os.getenv("CI"):
        options.binary_location = "/usr/bin/firefox"

    driver = webdriver.Firefox(options=options)
    try:
        driver.get(FIA_DOCS_URL)
        time.sleep(5)
        html = driver.page_source
        with open("fia_page_dump.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("✅ Dumped FIA page source to fia_page_dump.html")
        return html
    finally:
        driver.quit()

def extract_fia_docs(html):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="views-table")
    if not table:
        print("‼️ Could not find FIA document table.")
        return []

    rows = table.select("tbody tr")
    docs = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 2:
            continue
        title = cols[0].text.strip()
        if not title.lower().startswith("doc"):
            continue
        link_tag = cols[0].find("a")
        if not link_tag:
            continue
        link = "https://www.fia.com" + link_tag["href"]
        docs.append({"title": title, "link": link})
    return docs

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
            "description": "📄 New FIA F1 document released.",
            "color": 0x3498DB,
            "footer": {"text": "FIA F1 Document Update"}
        }]
    }
    res = requests.post(WEBHOOK_URL, json=payload)
    res.raise_for_status()

def main():
    html = get_page_html()
    docs = extract_fia_docs(html)
    if not docs:
        print("No documents found — exiting.")
        return

    last_hash = load_last_hash()
    new_hashes = []

    for doc in reversed(docs):  # oldest to newest
        doc_hash = compute_doc_hash(doc)
        new_hashes.append(doc_hash)

        if doc_hash == last_hash:
            print(f"Skipping already-posted doc: {doc['title']}")
            continue

        print(f"Posting new document: {doc['title']}")
        post_to_discord(doc)

    if new_hashes:
        save_last_hash(new_hashes[-1])

if __name__ == "__main__":
    main()