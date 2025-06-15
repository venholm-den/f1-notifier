import os
import time
import hashlib
import datetime
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By

WEBHOOK_URL = os.getenv("F1_DOCS_WEBHOOK")
FIA_DOCS_URL = "https://www.fia.com/documents/fia-formula-one-world-championship/2025"
HASH_FILE = "last_fia_doc_hash.txt"

def get_saved_hashes():
    if not os.path.exists(HASH_FILE):
        return set()
    with open(HASH_FILE, "r") as f:
        return set(line.strip() for line in f.readlines())

def save_hashes(hashes):
    with open(HASH_FILE, "w") as f:
        for h in sorted(hashes):
            f.write(h + "\n")

def hash_text(text):
    return hashlib.sha256(text.encode()).hexdigest()

def find_latest_docs():
    print("🚀 Launching Firefox with Selenium...")
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(options=options)

    try:
        print(f"🌍 Loading: {FIA_DOCS_URL}")
        driver.get(FIA_DOCS_URL)
        time.sleep(5)  # Wait for JS to load

        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()

        all_sections = soup.select("div.view-fia-documents div.view-group")
        if not all_sections:
            print("❌ No document sections found.")
            return []

        # Always use the first GP section
        first_section = all_sections[0]
        docs = []

        for row in first_section.select("div.views-row"):
            link_tag = row.find("a", href=True)
            if not link_tag or "Doc" not in link_tag.text:
                continue
            doc_title = link_tag.text.strip()
            doc_url = "https://www.fia.com" + link_tag["href"]

            docs.append((doc_title, doc_url))

        print(f"✅ Found {len(docs)} documents.")
        return docs

    except Exception as e:
        print(f"🔥 Error: {e}")
        driver.quit()
        return []

def post_to_discord(title, url):
    content = f"📄 **{title}**\n🔗 {url}"
    response = requests.post(WEBHOOK_URL, json={"content": content})
    if response.status_code == 204:
        print(f"✅ Posted: {title}")
    else:
        print(f"⚠️ Failed to post: {title}, HTTP {response.status_code}")

def main():
    posted_hashes = get_saved_hashes()
    docs = find_latest_docs()

    new_hashes = set(posted_hashes)
    for title, url in docs:
        h = hash_text(title)
        if h not in posted_hashes:
            post_to_discord(title, url)
            new_hashes.add(h)
        else:
            print(f"🕵️ Already posted: {title}")

    save_hashes(new_hashes)

if __name__ == "__main__":
    main()
