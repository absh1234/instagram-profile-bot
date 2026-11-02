
import os
import re
import requests
import instaloader

from urllib.parse import urlparse
from http.server import BaseHTTPRequestHandler


BOT_TOKEN = os.environ["BOT_TOKEN"]

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(chat_id, text):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text
        },
        timeout=20
    )


def send_document(chat_id, image_url, username):
    response = requests.get(
        image_url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )
    response.raise_for_status()

    files = {
        "document": (
            f"{username}_profile.jpg",
            response.content,
            "image/jpeg"
        )
    }

    requests.post(
        f"{TELEGRAM_API}/sendDocument",
        data={"chat_id": chat_id},
        files=files,
        timeout=50
    ).raise_for_status()


def extract_username(text):
    text = text.strip()

    if "instagram.com" in text:
        parsed = urlparse(
            text if "://" in text else "https://" + text
        )
        username = parsed.path.strip("/").split("/")[0]
    else:
        username = text.lstrip("@").strip()

    if not re.fullmatch(r"[A-Za-z0-9._]{1,30}", username):
        raise ValueError("Invalid username")

    return username


def get_profile_picture(username):
    loader = instaloader.Instaloader()

    profile = instaloader.Profile.from_username(
        loader.context,
        username
    )

    return profile.profile_pic_url


def process_update(update):
    message = update.get("message", {})

    if not message:
        return

    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    if text == "/start":
        send_message(
            chat_id,
            "Instagram Profile Downloader\n\n"
            "Send an Instagram username or profile link."
        )
        return

    try:
        username = extract_username(text)

        send_message(
            chat_id,
            f"Downloading @{username} ..."
        )

        image_url = get_profile_picture(username)

        send_document(
            chat_id,
            image_url,
            username
        )

        send_message(
            chat_id,
            f"Successfully downloaded @{username} profile picture."
        )

    except ValueError:
        send_message(chat_id, "Invalid Instagram username or link.")

    except Exception as error:
        print("ERROR:", error)
        send_message(
            chat_id,
            "Could not download this profile picture. "
            "The profile may be unavailable or Instagram "
            "may have restricted access."
        )


class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path != "/api/webhook":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        import json
        update = json.loads(body)

        process_update(update)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Instagram Bot is running")
