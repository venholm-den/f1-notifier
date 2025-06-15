import os
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

WEBHOOK_URL = os.getenv("F1_DOCS_WEBHOOK")
FIA_DOCS_URL = "https://www.fia.com/documents/fia-formula-one-world-championship/2025"
HASH_FILE = "last_fia_doc_hash.txt"

def get_saved_hashes():
    if not os.path.exists(HASH_FILE):
        return set()
    with open(HASH_FILE, "r") as f:
        return set(line.strip() for line in f)

def save_hashes(hashes):
    with open(HASH_FILE, "w") as f:
        for h in sorted(hashes):
            f.write(h + "\n")

def hash_text(text):
    return hashlib.sha256(text.encode()).hexdigest()

def find_latest_docs():
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(options=options)

    try:
        driver.get(FIA_DOCS_URL)
        time.sleep(5)  # Wait for page to fully load

        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()

        all_sections = soup.select("div.view-fia-documents div.view-group")
        if not all_sections:
            print("❌ No GP document sections found.")
            return []

        # Only use first (most recent) section
        first_section = all_sections[0]
        docs = []

        for row in first_section.select("div.views-row"):
            link = row.find("a", href=True)
            if link and "Doc" in link.text:
                title = link.text.strip()
                url = "https://www.fia.com" + link["href"]
                docs.append((title, url))

        return docs

    except Exception as e:
        driver.quit()
        print(f"🔥 Error during scraping: {e}")
        return []

def post_to_discord(title, url):
    content = f"📄 **{title}**\n🔗 {url}"
    r = requests.post(WEBHOOK_URL, json={"content": content})
    if r.status_code == 204:
        print(f"✅ Posted: {title}")
    else:
        print(f"❌ Failed to post {title}, HTTP {r.status_code}")

def main():
    posted_hashes = get_saved_hashes()
    new_hashes = set(posted_hashes)

    docs = find_latest_docs()
    for title, url in docs:
        doc_hash = hash_text(title)
        if doc_hash not in posted_hashes:
            post_to_discord(title, url)
            new_hashes.add(doc_hash)
        else:
            print(f"⏭️ Skipped already posted: {title}")

    save_hashes(new_hashes)

if __name__ == "__main__":
    main()
