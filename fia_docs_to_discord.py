import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import hashlib

WEBHOOK_URL = os.getenv("F1_DOCS_WEBHOOK")
LAST_HASH_FILE = "last_fia_doc_hash.txt"
FIA_URL = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season/season-2025-2071"

F1_WEEKENDS = [
    ("2025-03-14", "2025-03-16"),
    ("2025-03-21", "2025-03-23"),
    ("2025-04-04", "2025-04-06"),
    ("2025-04-11", "2025-04-13"),
    ("2025-04-18", "2025-04-20"),
    ("2025-05-02", "2025-05-04"),
    ("2025-05-16", "2025-05-18"),
    ("2025-05-23", "2025-05-25"),
    ("2025-05-30", "2025-06-01"),
    ("2025-06-13", "2025-06-15"),
    ("2025-06-27", "2025-06-29"),
    ("2025-07-04", "2025-07-06"),
    ("2025-07-25", "2025-07-27"),
    ("2025-08-01", "2025-08-03"),
    ("2025-08-29", "2025-08-31"),
    ("2025-09-05", "2025-09-07"),
    ("2025-09-19", "2025-09-21"),
    ("2025-10-03", "2025-10-05"),
    ("2025-10-17", "2025-10-19"),
    ("2025-10-24", "2025-10-26"),
    ("2025-11-07", "2025-11-09"),
    ("2025-11-21", "2025-11-23"),
    ("2025-11-28", "2025-11-30"),
    ("2025-12-05", "2025-12-07"),
]

def get_race_window_status():
    today = datetime.utcnow().date()
    for start_str, end_str in F1_WEEKENDS:
        start = datetime.strptime(start_str, "%Y-%m-%d").date()
        end = datetime.strptime(end_str, "%Y-%m-%d").date()
        if start <= today <= end:
            return "race"
    return "off"

def get_docs_from_today():
    res = requests.get(FIA_URL)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    table = soup.select_one("table.views-table")
    if not table:
        print("⚠️ FIA document table not found.")
        return []

    rows = table.select("tbody tr")
    if not rows:
        print("⚠️ No document rows found.")
        return []

    today = datetime.utcnow().strftime("%d.%m.%Y")
    docs = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 2:
            continue
        published = cols[-1].text.strip()
        if today != published:
            continue
        title = cols[0].text.strip()
        link = "https://www.fia.com" + cols[0].find("a")["href"]
        docs.append({"title": title, "link": link, "published": published})

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
            "description": f"📄 Published: {doc['published']}",
            "color": 0x3498DB,
            "footer": {"text": "FIA F1 Document Update"}
        }]
    }
    res = requests.post(WEBHOOK_URL, json=payload)
    res.raise_for_status()

def main():
    status = get_race_window_status()
    now = datetime.utcnow()

    if status == "off" and not (now.hour == 6 and now.minute < 15):
        print(f"Not a race weekend and not early morning — skipping ({now.time()})")
        return

    docs = get_docs_from_today()
    if not docs:
        print("No documents from today — exiting.")
        return

    last_hash = load_last_hash()
    new_hashes = []

    for doc in reversed(docs):  # Oldest to newest
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
