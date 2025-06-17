import time
import os
import requests
import hashlib
import fitz  # PyMuPDF
import discord
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup

FIA_DOCS_URL = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season/season-2025-2071"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
ERROR_WEBHOOK_URL = os.getenv("DISCORD_ERROR_WEBHOOK_URL")
CACHE_FILE = "last_fia_doc_hash.txt"

def get_rendered_html():
    print("🚀 Launching Firefox with Selenium...")
    options = Options()
    options.headless = True
    try:
        driver = webdriver.Firefox(options=options)
    except Exception as e:
        print("❌ Failed to start Firefox via Selenium.")
        raise e
    try:
        print("🌐 Opening FIA 2025 documents page...")
        driver.get(FIA_DOCS_URL)
        time.sleep(5)
        return driver.page_source
    finally:
        driver.quit()

def extract_pdf_links(html):
    soup = BeautifulSoup(html, "html.parser")
    return [
        a["href"] if a["href"].startswith("http") else f"https://www.fia.com{a['href']}"
        for a in soup.find_all("a", href=True)
        if a["href"].endswith(".pdf")
    ]

def load_cached_hashes():
    if not os.path.exists(CACHE_FILE):
        return set()
    with open(CACHE_FILE, "r") as f:
        return set(line.strip() for line in f.readlines())

def save_cached_hashes(hashes):
    with open(CACHE_FILE, "w") as f:
        f.writelines(h + "\n" for h in sorted(hashes))

def hash_url(url):
    return hashlib.sha256(url.encode()).hexdigest()

def download_pdf(url, folder):
    filename = url.split("/")[-1]
    path = os.path.join(folder, filename)
    r = requests.get(url)
    r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)
    return path

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

    # ✅ Fixed unterminated regex (was `[^]`, now `[^\\n]`)
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

    files = [discord.File(img) for img in image_paths]
    webhook = discord.SyncWebhook.from_url(WEBHOOK_URL)
    webhook.send(content=content, files=files)

def is_race_weekend():
    return datetime.utcnow().strftime("%A") in ["Friday", "Saturday", "Sunday"]

def report_error_to_discord(error_msg):
    if ERROR_WEBHOOK_URL:
        try:
            webhook = discord.SyncWebhook.from_url(ERROR_WEBHOOK_URL)
            webhook.send(content=f"❌ FIA Scraper Error:\n```\n{error_msg}\n```")
        except Exception as e:
            print(f"⚠️ Failed to send error to Discord: {e}")
    else:
        print("⚠️ DISCORD_ERROR_WEBHOOK_URL not set")

def main():
    if not is_race_weekend():
        print("⏭️ Not a race weekend. Exiting.")
        return

    try:
        html = get_rendered_html()
        pdf_links = extract_pdf_links(html)
        print(f"📄 Found {len(pdf_links)} PDF documents.")

        os.makedirs("fia_docs", exist_ok=True)
        os.makedirs("jpg_output", exist_ok=True)
        cache = load_cached_hashes()
        new_cache = set(cache)

        for url in pdf_links:
            h = hash_url(url)
            if h in cache:
                print(f"⏩ Skipping cached document: {url}")
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

    except Exception as e:
        report_error_to_discord(f"Top-level failure:\n{e}")

if __name__ == "__main__":
    main()
