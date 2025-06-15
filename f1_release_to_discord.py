import requests
import os
from datetime import datetime

# CONFIGURATION
REPO = "f1-docs"  # GitHub repo in format: owner/repo, e.g., "fia-org/f1-docs"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Load from GitHub secret or local env var
LAST_RELEASE_FILE = "last_release.txt"

# 2025 F1 Race Weekends (Friday to Sunday)
F1_WEEKENDS = [
    ("2025-03-14", "2025-03-16"),  # Australia
    ("2025-03-21", "2025-03-23"),  # China (Sprint)
    ("2025-04-04", "2025-04-06"),  # Japan
    ("2025-04-11", "2025-04-13"),  # Bahrain
    ("2025-04-18", "2025-04-20"),  # Saudi Arabia
    ("2025-05-02", "2025-05-04"),  # Miami (Sprint)
    ("2025-05-16", "2025-05-18"),  # Imola
    ("2025-05-23", "2025-05-25"),  # Monaco
    ("2025-05-30", "2025-06-01"),  # Spain
    ("2025-06-13", "2025-06-15"),  # Canada
    ("2025-06-27", "2025-06-29"),  # Austria
    ("2025-07-04", "2025-07-06"),  # Britain
    ("2025-07-25", "2025-07-27"),  # Belgium (Sprint)
    ("2025-08-01", "2025-08-03"),  # Hungary
    ("2025-08-29", "2025-08-31"),  # Netherlands
    ("2025-09-05", "2025-09-07"),  # Italy
    ("2025-09-19", "2025-09-21"),  # Azerbaijan
    ("2025-10-03", "2025-10-05"),  # Singapore
    ("2025-10-17", "2025-10-19"),  # USA (Austin) - Sprint
    ("2025-10-24", "2025-10-26"),  # Mexico
    ("2025-11-07", "2025-11-09"),  # Brazil - Sprint
    ("2025-11-21", "2025-11-23"),  # Las Vegas
    ("2025-11-28", "2025-11-30"),  # Qatar - Sprint
    ("2025-12-05", "2025-12-07"),  # Abu Dhabi
]

def is_f1_weekend_today():
    today = datetime.utcnow().date()
    for start_str, end_str in F1_WEEKENDS:
        start = datetime.strptime(start_str, "%Y-%m-%d").date()
        end = datetime.strptime(end_str, "%Y-%m-%d").date()
        if start <= today <= end:
            return True
    return False

def get_latest_release(repo):
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def load_last_release():
    if not os.path.exists(LAST_RELEASE_FILE):
        return None
    with open(LAST_RELEASE_FILE, "r") as f:
        return f.read().strip()

def save_last_release(tag):
    with open(LAST_RELEASE_FILE, "w") as f:
        f.write(tag)

def post_to_discord(release):
    if not WEBHOOK_URL:
        raise EnvironmentError("WEBHOOK_URL is not set in environment variables.")
    
    title = release["name"] or release["tag_name"]
    url = release["html_url"]
    body = release["body"] or "*No description provided.*"
    
    content = f"🚀 **New Release** for `{REPO}`\n**{title}**\n{url}\n\n{body[:1000]}"
    payload = {"content": content}
    
    response = requests.post(WEBHOOK_URL, json=payload)
    response.raise_for_status()

def main():
    if not is_f1_weekend_today():
        print(f"Today is not an F1 weekend ({datetime.utcnow().date()}). Exiting.")
        return

    release = get_latest_release(REPO)
    latest_tag = release["tag_name"]
    last_tag = load_last_release()

    if latest_tag != last_tag:
        print(f"New release found: {latest_tag}")
        post_to_discord(release)
        save_last_release(latest_tag)
    else:
        print("No new release.")

if __name__ == "__main__":
    main()
