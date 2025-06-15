# fia_docs_to_discord.py

import os
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

FIA_DOCS_URL = "https://www.fia.com/documents"
DISCORD_WEBHOOK_URL = os.getenv("F1_DOCS_WEBHOOK")
DUMP_HTML = "fia_page_dump.html"
HASH_FILE = "last_fia_doc_hash.txt"

def get_docs():
    print("🦊 Launching Firefox headless...")
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(options=options)
    driver.get(FIA_DOCS_URL)
    time.sleep(5)

    html = driver.page_source
    with open(DUMP_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Dumped FIA page source.")

    soup = BeautifulSoup(html, "html.parser")
    doc_table = soup.find("table", class_="views-table")
    if not doc_table:
        print("‼️ Could not find FIA document table.")
        driver.quit()
        return []

    rows = doc_table.find_all("tr")
    docs = []
    for row in rows:
        link = row.find("a", href=True)
        if link and "Doc" in link.text:
            title = link.text.strip()
            href = "https://www.fia.com" + link['href']
            docs.append({"title": title, "url": href})
    driver.quit()
    print(f"📄 Found {len(docs)} Doc entries.")
    return docs

def hash_doc(doc):
    return hashlib.sha256((doc['title'] + doc['url']).encode()).hexdigest()

def read_last_hash():
    if not os.path.exists(HASH_FILE):
        return None
    with open(HASH_FILE, "r") as f:
        return f.read().strip()

def write_last_hash(h):
    with open(HASH_FILE, "w") as f:
        f.write(h)

def post_to_discord(doc):
    content = f"📎 New FIA Document Posted:\n**{doc['title']}**\n{doc['url']}"
    r = requests.post(DISCORD_WEBHOOK_URL, json={"content": content})
    print("📤 Posted to Discord:", r.status_code)

def main():
    docs = get_docs()
    if not docs:
        return
    latest = docs[0]
    latest_hash = hash_doc(latest)
    if latest_hash != read_last_hash():
        post_to_discord(latest)
        write_last_hash(latest_hash)
    else:
        print("⏸ No new document — skipping post.")

if __name__ == "__main__":
    main()
