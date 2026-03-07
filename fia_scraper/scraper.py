import time
import os
import requests
import hashlib
from urllib.parse import urlparse
import fitz  # PyMuPDF for reading and rendering PDFs
# Post to Discord via webhook (no bot token required)
import re
import sys
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import json

# Formula 1 calendar
RACE_DATES = [
    "2025-03-16", # Australian GP — Melbourne
    "2026-03-08",  # Australian GP — Melbourne
    "2026-03-15",  # Chinese GP — Shanghai
    "2026-03-29",  # Japanese GP — Suzuka
    "2026-04-12",  # Bahrain GP — Sakhir
    "2026-04-19",  # Saudi Arabian GP — Jeddah
    "2026-05-03",  # Miami GP — Miami
    "2026-05-24",  # Canadian GP — Montreal
    "2026-06-07",  # Monaco GP — Monaco
    "2026-06-14",  # Spanish GP — Barcelona-Catalunya
    "2026-06-28",  # Austrian GP — Spielberg
    "2026-07-05",  # British GP — Silverstone
    "2026-07-19",  # Belgian GP — Spa
    "2026-07-26",  # Hungarian GP — Budapest
    "2026-08-23",  # Dutch GP — Zandvoort
    "2026-09-06",  # Italian GP — Monza
    "2026-09-13",  # Spanish GP — Madrid
    "2026-09-26",  # Azerbaijan GP — Baku
    "2026-10-11",  # Singapore GP — Singapore
    "2026-10-25",  # United States GP — Austin
    "2026-11-01",  # Mexico City GP — Mexico City
    "2026-11-08",  # São Paulo GP — Interlagos
    "2026-11-21",  # Las Vegas GP — Las Vegas
    "2026-11-29",  # Qatar GP — Lusail
    "2026-12-06",  # Abu Dhabi GP — Yas Marina
]

# FIA documents base URL for 2026 season
FIA_DOCS_URL = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season/season-2026-2072"

# Discord webhook environment variables
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
ERROR_WEBHOOK_URL = os.getenv("DISCORD_ERROR_WEBHOOK_URL")

# Cache file path to store hashes of already-processed documents
CACHE_FILE = "last_fia_doc_hash.txt"

# Fetch FIA documents page HTML
# NOTE: The FIA documents list is server-rendered (PDF links appear in raw HTML),
# so we avoid Selenium/Firefox for reliability and speed.
def get_rendered_html():
    print("🌐 Fetching FIA 2026 documents page...")
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    r = requests.get(FIA_DOCS_URL, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text

# Extract all PDF links from the rendered HTML
def extract_pdf_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href.lower().endswith(".pdf"):
            continue
        if href.startswith("http"):
            links.append(href)
        else:
            links.append(f"https://www.fia.com{href}")
    # Deduplicate while preserving order
    seen = set()
    out = []
    for u in links:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out

# Load previously seen document hashes from cache file
def load_cached_hashes():
    if not os.path.exists(CACHE_FILE):
        return set()
    with open(CACHE_FILE, "r") as f:
        return set(line.strip() for line in f.readlines())

# Save updated list of hashes to cache file
def save_cached_hashes(hashes):
    with open(CACHE_FILE, "w") as f:
        f.writelines(h + "\n" for h in sorted(hashes))

# SHA256 hash of the document identifier (used for cache comparison)
# We canonicalize to the URL path so scheme/host changes (http vs https) don't break caching.
def hash_url(url):
    try:
        path = urlparse(url).path
    except Exception:
        path = url
    key = path.strip().lower()
    return hashlib.sha256(key.encode()).hexdigest()

# Download a PDF file to a specified folder
def download_pdf(url, folder):
    filename = url.split("/")[-1]
    path = os.path.join(folder, filename)
    r = requests.get(url)
    r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)
    return path

# Extract structured metadata from the first page of a PDF document
def extract_pdf_metadata(pdf_path):
    doc = fitz.open(pdf_path)
    first_page_text = doc[0].get_text()

    doc_match = re.search(r"Document\s+(\d+)", first_page_text)
    doc_number = doc_match.group(1) if doc_match else "Unknown"

    event_match = re.search(r"(\d{4}\s+.*?Grand Prix)", first_page_text, re.IGNORECASE)
    event = event_match.group(1).title().replace("  ", " ") if event_match else "Event Unknown"

    date_match = re.search(r"Date\s+([0-9]{1,2}\s+[A-Za-z]+\s+\d{4})", first_page_text)
    time_match = re.search(r"Time\s+([0-9]{2}:[0-9]{2})", first_page_text)
    date = date_match.group(1).strip() if date_match else ""
    time_str = time_match.group(1).strip() if time_match else ""

    driver_match = re.search(r"No\s*/\s*Driver\s+(\d+)\s*[-–]\s*(.+)", first_page_text)
    driver_info = f"{driver_match.group(1)} – {driver_match.group(2).strip()}" if driver_match else ""

    reason_match = re.search(r"Reason\s+([^\n]+)", first_page_text)
    reason = reason_match.group(1).strip() if reason_match else ""

    title_match = re.search(
        r"(Summons|Decision|Infringement|Classification|Points|Notes|Report|Scrutineering|Grid|Procedure|Entry List|Car Presentation)",
        first_page_text, re.IGNORECASE)
    title = title_match.group(1).title() if title_match else os.path.basename(pdf_path).split(".")[0].replace("_", " ").title()

    return {
        "doc_num": doc_number,
        "title": title,
        "driver_info": driver_info,
        "event": event,
        "date": date,
        "time": time_str,
        "reason": reason
    }

# Convert a multi-page PDF into JPEG images (150 DPI)
def convert_pdf_to_images(pdf_path, image_folder, base_name=None):
    os.makedirs(image_folder, exist_ok=True)
    doc = fitz.open(pdf_path)
    image_paths = []
    for i in range(len(doc)):
        page = doc.load_page(i)
        pix = page.get_pixmap(dpi=150)
        name = base_name or os.path.basename(pdf_path)
        img_path = os.path.join(image_folder, f"{name}_page_{i+1}.jpg")
        pix.save(img_path)
        image_paths.append(img_path)
    return image_paths

def _send_webhook_files(webhook_url: str, content: str | None, file_paths: list[str]):
    # Discord webhooks accept multipart with files[0], files[1], ...
    files = {}
    opened = []
    try:
        for idx, p in enumerate(file_paths):
            f = open(p, "rb")
            opened.append(f)
            files[f"files[{idx}]"] = (p.split("/")[-1], f, "image/jpeg")

        data = {
            "payload_json": json.dumps({"content": content or ""}),
        }
        r = requests.post(webhook_url, data=data, files=files, timeout=60)
        r.raise_for_status()
    finally:
        for f in opened:
            try:
                f.close()
            except Exception:
                pass


# Format and post metadata + images to Discord via webhook
def post_images_to_discord(image_paths, metadata):
    doc_num = metadata.get("doc_num", "Unknown")
    title = metadata.get("title", "Untitled")
    driver_info = metadata.get("driver_info", "")
    event = metadata.get("event", "")
    date = metadata.get("date", "")
    time_str = metadata.get("time", "")
    reason = metadata.get("reason", "")

    bold_line = f"**Doc {doc_num} — {title}"
    if driver_info:
        bold_line += f" — {driver_info}"
    bold_line += "**"

    plain_line = ""
    if event != "Event Unknown" and event.strip():
        plain_line = f"{event} — {date} — {time_str}".strip(" —")

    content = bold_line
    if plain_line:
        content += f"\n{plain_line}"
    if reason:
        content += f"\n_{reason}_"

    for i in range(0, len(image_paths), 10):
        chunk = image_paths[i:i+10]
        _send_webhook_files(WEBHOOK_URL, content if i == 0 else None, chunk)

# Check if today is within ±2 days of a race date
def is_race_weekend():
    today = datetime.utcnow().date()
    race_dates = [datetime.strptime(d, "%Y-%m-%d").date() for d in RACE_DATES]
    for race_day in race_dates:
        if abs((race_day - today).days) <= 2:
            return True
    return False

# Report unexpected errors to Discord error channel
def report_error_to_discord(error_msg):
    if ERROR_WEBHOOK_URL:
        try:
            webhook = discord.SyncWebhook.from_url(ERROR_WEBHOOK_URL)
            webhook.send(content=f"❌ FIA Scraper Error:\n```{error_msg}\n```")
        except Exception as e:
            print(f"⚠️ Failed to send error to Discord: {e}")
    else:
        print("⚠️ DISCORD_ERROR_WEBHOOK_URL not set")

# Main scraping and processing routine
def main():
    # Hard safety cap: if the scraper ever thinks there are "too many" new docs,
    # treat it as a state/caching failure and do not spam Discord.
    MAX_NEW_DOCS_PER_RUN = int(os.getenv("MAX_NEW_DOCS_PER_RUN", "10"))
    # Check for `--force` flag to override race weekend logic
    force = "--force" in sys.argv

    # Skip if not a race weekend unless force override is active
    if not force and not is_race_weekend():
        print("⏭️ Not a race weekend. Exiting. Use --force to override.")
        return

    try:
        html = get_rendered_html()
        pdf_links = extract_pdf_links(html)
        print(f"📄 Found {len(pdf_links)} PDF documents.")

        os.makedirs("fia_docs", exist_ok=True)
        os.makedirs("jpg_output", exist_ok=True)
        cache = load_cached_hashes()
        new_cache = set(cache)

        print(f"🧾 Cache entries loaded: {len(cache)}")

        # First-run safety: if the cache is empty, do NOT post everything.
        # Instead, initialize the cache with the current set and exit.
        # Use --force if you intentionally want to post everything.
        if not cache and not force:
            print(f"🧯 Cache is empty. Initializing cache with {len(pdf_links)} existing docs (no posts).")
            for url in pdf_links:
                new_cache.add(hash_url(url))
            save_cached_hashes(new_cache)
            print(f"🧾 Cache entries saved: {len(new_cache)}")
            return

        # Safety cap: if we detect too many "new" docs in one run, assume the cache/state is wrong.
        unseen = [u for u in pdf_links if hash_url(u) not in cache]
        if len(unseen) > MAX_NEW_DOCS_PER_RUN:
            msg = (
                f"🚨 Safety stop: detected {len(unseen)} new docs (limit {MAX_NEW_DOCS_PER_RUN}). "
                "This looks like a cache/state failure; refusing to post to avoid spam. "
                "If this is intentional, raise MAX_NEW_DOCS_PER_RUN or run with a known-good cache."
            )
            print(msg)
            report_error_to_discord(msg)
            # Still update cache so the next run can recover without spamming.
            for url in pdf_links:
                new_cache.add(hash_url(url))
            save_cached_hashes(new_cache)
            print(f"🧾 Cache entries saved: {len(new_cache)}")
            return

        for url in pdf_links:
            h = hash_url(url)
            if h in cache:
                print(f"⏩ Skipping cached document: {url}")
                new_cache.add(h)
                continue
            
            try:
                print(f"⬇️ Downloading and processing: {url}")
                pdf_path = download_pdf(url, "fia_docs")
                metadata = extract_pdf_metadata(pdf_path)

                base_name = f"Doc_{metadata['doc_num']}_{metadata['title'].replace(' ', '_')}"
                base_name = re.sub(r"[^\w\-_.]", "", base_name)

                images = convert_pdf_to_images(pdf_path, "jpg_output", base_name=base_name)
                post_images_to_discord(images, metadata)
                new_cache.add(h)

            except Exception as e:
                err_msg = f"{url}\n{e}"
                print(f"❌ Error handling {url}: {e}")
                report_error_to_discord(err_msg)

        save_cached_hashes(new_cache)
        print(f"🧾 Cache entries saved: {len(new_cache)}")

    except Exception as e:
        report_error_to_discord(f"Top-level failure:\n{e}")

if __name__ == "__main__":
    main()
