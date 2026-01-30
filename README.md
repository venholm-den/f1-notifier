# f1-notifier

Two small automations that post into Discord via webhooks:

1) **FIA Documents** → downloads FIA decision PDFs, renders pages as images, posts to `#fia-documents`.
2) **F1 Weekend** → posts race-weekend cards (schedule/track/weather/countdown/quali/sprint/results/standings, etc.) to `#f1-weekend`.

Everything runs on **GitHub Actions**.

## Requirements

Python deps (shared for both workflows):
- `requests`
- `beautifulsoup4`
- `PyMuPDF`
- `Pillow` (for simple PNG “cards”)

Install:
```bash
pip install -r requirements.txt
```

## Secrets (GitHub → Settings → Secrets and variables → Actions)

### FIA scraper
- `DISCORD_WEBHOOK_URL` — destination channel webhook (e.g. `#fia-documents`)
- `DISCORD_ERROR_WEBHOOK_URL` — error/alert webhook (e.g. `#incidents`)

### F1 weekend autoposter
- `DISCORD_F1_WEEKEND_WEBHOOK_URL` — destination channel webhook (e.g. `#f1-weekend`)

## Workflows

### 1) FIA scraper
Workflow: `.github/workflows/fia_scraper.yml`

Notes:
- Uses a local cache file (`last_fia_doc_hash.txt`) + GitHub Actions cache to avoid duplicates.
- **Anti-spam safety cap:** if the scraper detects more than `MAX_NEW_DOCS_PER_RUN` “new” docs (default **10**) in a single run, it **refuses to post** (and alerts via `DISCORD_ERROR_WEBHOOK_URL`) to avoid flooding Discord. You can raise/lower the cap by setting `MAX_NEW_DOCS_PER_RUN` in the workflow env.

Manual run:
```bash
python fia_scraper/scraper.py --force
```

### 2) F1 weekend autoposter
Workflow: `.github/workflows/f1_weekend.yml`

Notes:
- Scheduled runs execute in `auto` mode and **only post during race weekends** (Thu→Mon window around the next race, UTC).
- Posts are de-duped with `f1_weekend_state.json` (cached in Actions).

Local manual test:
```bash
F1_WEEKEND_FORCE=true F1_WEEKEND_MODE=schedule python -c "from f1_weekend.post import post_weekend_update; post_weekend_update('schedule')"
```

## Housekeeping

- No Selenium/Firefox: FIA page contains PDF links in raw HTML.
- No `discord.py`: all posting is done via Discord webhooks with `requests`.

Built by @venholm-den.
