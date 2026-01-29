import json
import requests


def send_webhook(webhook_url: str, content: str, file_bytes: bytes | None = None, filename: str | None = None):
    if not webhook_url:
        raise RuntimeError("Missing webhook url")

    if file_bytes is None:
        r = requests.post(webhook_url, json={"content": content})
        r.raise_for_status()
        return

    files = {
        "files[0]": (filename or "image.png", file_bytes, "image/png"),
    }
    data = {
        "payload_json": json.dumps({"content": content}),
    }
    r = requests.post(webhook_url, data=data, files=files)
    r.raise_for_status()
