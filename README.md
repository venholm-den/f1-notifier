# 🏎️ FIA F1 Document Scraper

This project automatically scrapes official FIA PDF documents for each Formula 1 Grand Prix (summons, decisions, classifications, etc.) and posts them to a Discord channel as image previews.

---

## 📆 Features

- Scrapes PDFs from the [FIA 2025 F1 Documents page](https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season/season-2025-2071)
- Extracts metadata (Doc #, title, driver, reason, event, date, time)
- Converts PDF pages to JPEGs and posts to Discord via webhook
- Caches previously posted documents to avoid duplicates
- Runs automatically on GitHub Actions:
  - **Every 5 minutes** on race weekends
  - **Once per day** on non-race days
- Error alerts are sent to a separate Discord channel

---

## 🧰 Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/f1-notifier.git
cd f1-notifier
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `discord.py`
- `requests`
- `beautifulsoup4`
- `PyMuPDF`
- `selenium`

### 3. Environment variables

Create a `.env` file or export these in your shell or CI:

```env
DISCORD_WEBHOOK_URL=your_discord_webhook
DISCORD_ERROR_WEBHOOK_URL=your_error_channel_webhook
```

---

## ⚙️ GitHub Actions

The workflow is defined in `.github/workflows/fia_scraper.yml`.

It runs:

- **Every 5 minutes**: `cron: '*/5 * * * *'`
- The Python script will skip if it's not a race weekend (±2 days of a listed race date)
- Race weekends are hardcoded in the script (`RACE_DATES_2025`)

You can also run the workflow manually from the GitHub UI.

---

## 📁 Project Structure

```text
fia_scraper/
├── scraper.py              # Main scraper logic
├── last_fia_doc_hash.txt   # Cache of previously seen documents
.github/
└── workflows/
    └── fia_scraper.yml     # GitHub Actions CI runner
```

---

## 🛠️ Developer Notes

- Uses headless Firefox with Selenium to render JavaScript-based PDF links
- Converts PDFs to 150 DPI JPEGs with PyMuPDF for Discord image display
- Supports up to 10 images per Discord message (splits longer PDFs)
- Automatically formats and posts detailed messages with doc metadata

---

## 🧪 Manual Run (Local)

To run manually on your machine:

```bash
python fia_scraper/scraper.py
```

---

## 📅 Updating the Calendar

Race weekends are hardcoded in `RACE_DATES_2025` inside `scraper.py`. Update as the official calendar changes.

```python
RACE_DATES_2025 = [
    "2025-03-16",  # Australia
    ...
]
```

---

## 🧼 To Do

- Auto-cleanup old JPEGs or archive them
- Optional: store metadata in JSON or DB
- Optional: Add retry/backoff for flaky PDF downloads
- Optional: Support for other FIA championships (F2, F3)

---

## 📬 Contact

Built by [@Kyle](https://github.com/venholm-den).  
Have suggestions or issues? Open an issue or PR!
