import os
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import hashlib

FIA_DOCUMENTS_URL = "https://www.fia.com/documents/f1-world-championship"
WEBHOOK_URL = os.environ.get("F1_DOCS_WEBHOOK")
HASH_CACHE_FILE = "last_fia_doc_hash.txt"
GECKO_LOG_FILE = "geckodriver.log"

# Set geckodriver log file
os.environ["GECKO_DRIVER_LOG"] = GECKO_LOG_FILE

def get_page_html():
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options)
    driver.get(FIA_DOCUMENTS_URL)
    html = driver.page_source
    driver.quit()
    return html

def get_posted_hashes():
    if os.path.exists(HASH_CACHE_FILE):
        with open(HASH_CACHE_FILE, "r") as f:
            return set(line.strip() for line in f)
    return set()

def save_posted_hashes(hashes):
    with open(HASH_CACHE_FILE, "w") as f:
        f.write("\n".join(hashes))

def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def find_new_docs(html, posted_hashes):
    soup = BeautifulSoup(html, "html.parser")
    sections = soup.select(".views-row")
    if not sections:
        print("❌ No document sections found.")
        return []

    doc_links = []
    for section in sections:
        doc_links.extend(section.select("a[href$='.pdf']"))

    new_docs = []
    for link in doc_links:
        title = link.text.strip()
        if not title.startswith("Doc"):
            continue
        url = link["href"]
        full_url = url if url.startswith("http") else f"https://www.fia.com{url}"
        doc_id = sha256(full_url)
        if doc_id not in posted_hashes:
            new_docs.append((title, full_url, doc_id))

    return new_docs

def send_to_discord(title, url):
    data = { "content": f"📄 **{title}**\n{url}" }
    response = requests.post(WEBHOOK_URL, json=data)
    return response.status_code == 204

def main():
    print("🚀 Launching Firefox with Selenium...")
    html = get_page_html()
    posted_hashes = get_posted_hashes()
    new_docs = find_new_docs(html, posted_hashes)

    if not new_docs:
        print("✅ No new documents found.")
        return

    print(f"📦 Found {len(new_docs)} new doc(s):")
    for title, url, doc_id in new_docs:
        if send_to_discord(title, url):
            print(f"✅ Sent to Discord: {title}")
            posted_hashes.add(doc_id)
        else:
            print(f"❌ Failed to send: {title}")

    save_posted_hashes(posted_hashes)

if __name__ == "__main__":
    main()
