import os
import re
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service as FirefoxService

WEBHOOK_URL = os.environ.get("F1_DOCS_WEBHOOK")
DUMP_HTML = True
HASH_CACHE_FILE = "last_fia_doc_hash.txt"
FIA_DOCUMENTS_URL = "https://www.fia.com/documents"
GECKO_LOG_PATH = "geckodriver.log"

# Used to track which docs we've already posted
def load_posted_hashes():
    try:
        with open(HASH_CACHE_FILE, "r") as f:
            return set(line.strip() for line in f.readlines())
    except FileNotFoundError:
        return set()

def save_posted_hashes(hashes):
    with open(HASH_CACHE_FILE, "w") as f:
        for h in sorted(hashes):
            f.write(h + "\n")

def hash_doc(title, url):
    return hashlib.sha256(f"{title}|{url}".encode()).hexdigest()

def post_to_discord(title, url):
    print(f"📣 Posting to Discord: {title}")
    response = requests.post(WEBHOOK_URL, json={"content": f"**{title}**\n{url}"})
    if response.status_code != 204:
        print(f"‼️ Failed to post: {response.status_code} - {response.text}")

def main():
    print("🚀 Launching headless Firefox...")

    options = Options()
    options.add_argument("--headless")
    os.environ["GECKO_DRIVER_LOG"] = GECKO_LOG_PATH
    driver = webdriver.Firefox(service=FirefoxService(), options=options)

    try:
        driver.get(FIA_DOCUMENTS_URL)
        time.sleep(4)
        page_source = driver.page_source

        if DUMP_HTML:
            with open("fia_page_dump.html", "w", encoding="utf-8") as f:
                f.write(page_source)
            print("✅ Dumped FIA page source to fia_page_dump.html")

        soup = BeautifulSoup(page_source, "html.parser")
        posted_hashes = load_posted_hashes()
        new_hashes = set()

        found_docs = False

        for link in soup.find_all("a", href=True):
            title = link.get_text(strip=True)
            if re.match(r"Doc\s+\d+", title, re.IGNORECASE):
                url = link["href"]
                if not url.startswith("http"):
                    url = "https://www.fia.com" + url

                doc_hash = hash_doc(title, url)

                if doc_hash not in posted_hashes:
                    found_docs = True
                    post_to_discord(title, url)
                    new_hashes.add(doc_hash)
                else:
                    print(f"🟡 Already posted: {title}")

        if not found_docs:
            print("ℹ️ No new 'Doc XX' documents found.")

        save_posted_hashes(posted_hashes.union(new_hashes))

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
