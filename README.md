# 🏎️ FIA Formula 1 Document Notifier

This Python-powered scraper monitors the FIA website for newly published Formula 1 documents (e.g. Summons, Decisions, Race Director Notes) and posts them — as images — directly to a Discord channel for quick access and visibility.

---

## 🚀 Features

- Scrapes the official [FIA F1 documents page](https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season/season-2025-2071)
- Extracts document metadata:
  - Document number (e.g. `Doc 57`)
  - Title (e.g. `Summons`, `Decision`)
  - Driver info (if applicable)
  - Event name, Date, and Time
  - Reason (if available)
- Converts PDFs to JPEG images (1 image per page)
- Posts each document (and its images) to a Discord channel
- Skips reposting already seen documents using a hash cache
- Posts any errors to a separate error webhook
- Automatically runs every 5 minutes **only on race weekends**

---

## 🛠️ Requirements

- Python 3.12+
- Firefox (headless via Selenium)
- Geckodriver
- Discord Webhook(s)

Install dependencies:
```bash
pip install -r requirements.txt
