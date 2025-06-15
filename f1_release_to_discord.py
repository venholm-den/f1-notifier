import requests
import os

REPO = "fia-org/f1-docs"  # Replace with your actual repo
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
LAST_RELEASE_FILE = "last_release.txt"

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
    title = release["name"] or release["tag_name"]
    url = release["html_url"]
    body = release["body"] or "*No description provided.*"
    content = f"🚀 **New Release** for `{REPO}`\n**{title}**\n{url}\n\n{body[:1000]}"
    payload = {"content": content}
    requests.post(WEBHOOK_URL, json=payload)

def main():
    release = get_latest_release(REPO)
    latest_tag = release["tag_name"]
    last_tag = load_last_release()

    if latest_tag != last_tag:
        print(f"New release: {latest_tag}")
        post_to_discord(release)
        save_last_release(latest_tag)
    else:
        print("No new release.")

if __name__ == "__main__":
    main()
