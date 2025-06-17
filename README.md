🏁 FIA Document Scraper

Automatically monitors and posts official FIA Formula 1 PDF documents (e.g., decisions, summons, classifications) to Discord during race weekends.
🔧 Features

    🕵️ Scrapes the FIA’s official documents page for F1 2025 season.

    📁 Renames and hashes documents to avoid re-posting duplicates.

    🖼️ Converts PDFs to images for cleaner previews in Discord.

    🧠 Extracts metadata (Doc number, driver, event, time, reason).

    📅 Only runs during race weekends, using live data from the Ergast F1 API.

    🧵 Posts nicely formatted messages with embedded images to Discord.

    🚨 Error reporting to a separate Discord webhook channel.

🧱 Project Structure

fia_scraper/
├── scraper.py              # Main logic
├── last_fia_doc_hash.txt   # Local cache of previously seen document hashes
├── fia_docs/               # Downloaded PDFs (runtime)
├── jpg_output/             # Converted images (runtime)
.github/
└── workflows/
    └── fia_scraper.yml     # GitHub Actions workflow file

🚀 Setup & Deployment
1. 🧪 Local Testing

pip install -r requirements.txt
export DISCORD_WEBHOOK_URL=your_webhook
export DISCORD_ERROR_WEBHOOK_URL=your_error_webhook
python fia_scraper/scraper.py

2. 🛰 GitHub Actions Deployment

The workflow runs every 10 minutes, but exits early unless a race weekend is detected:

on:
  schedule:
    - cron: '*/10 * * * *'

It uses:

    Firefox 127.0

    Geckodriver 0.34.0

    Python 3.12

3. 🔐 Secrets

Define these GitHub secrets in your repo:
Secret Name	Description
DISCORD_WEBHOOK_URL	Discord channel to post updates
DISCORD_ERROR_WEBHOOK_URL	Optional error log webhook
🧠 Race Weekend Detection

Uses the Ergast API to dynamically detect if a race is within ±2 days of today (UTC). This prevents unnecessary scraping during off weekends.
📎 Example Discord Post

**Doc 22 — Infringement — 55 – Carlos Sainz**
2025 Canadian Grand Prix — 9 June 2025 — 15:30
_Failed to follow safety car instructions._
[Attached: Page 1 of PDF]

🐛 Known Limitations

    FIA may change site structure without notice

    Limited to 10 images per Discord post (Discord API limit)

    Rate limits and large PDFs may occasionally trigger errors
