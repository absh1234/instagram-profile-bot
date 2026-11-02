import os
import re
import json
import hmac
import base64
import binascii
import logging
import requests
import instaloader

from urllib.parse import urlparse
from http.server import BaseHTTPRequestHandler


BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]
INSTAGRAM_USERNAME = os.environ.get("INSTAGRAM_USERNAME", "aryatrgrn").strip()

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InstagramSetupError(Exception):
    """An Instagram session/configuration problem that needs operator action."""


def telegram_request(method, data=None, files=None):
    response = requests.post(
        f"{TELEGRAM_API}/{method}",
        data=data,
        files=files,
        timeout=45
    )
    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(result.get("description", "Telegram API error"))

    return result


def send_message(chat_id, text):
    telegram_request(
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": text
        }
    )


def extract_username(text):
    text = text.strip()

    if "instagram.com" in text.lower():
        parsed = urlparse(
            text if "://" in text else "https://" + text
        )

        if parsed.netloc.lower() not in (
            "instagram.com",
            "www.instagram.com"
        ):
            raise ValueError("Invalid Instagram URL")

        username = parsed.path.strip("/").split("/")[0]
    else:
        username = text.lstrip("@").strip()

    if not re.fullmatch(r"[A-Za-z0-9._]{1,30}", username):
        raise ValueError("Invalid username")

    return username


def get_profile_picture(username):
    session_b64 = os.environ.get("INSTAGRAM_SESSION_B64")

    if not session_b64:
        raise InstagramSetupError("INSTAGRAM_SESSION_B64 is not configured")

    if not INSTAGRAM_USERNAME:
        raise InstagramSetupError("INSTAGRAM_USERNAME is empty")

    try:
        session_data = base64.b64decode(session_b64, validate=True)
    except (binascii.Error, ValueError) as error:
        raise InstagramSetupError(
            "INSTAGRAM_SESSION_B64 is not valid base64"
        ) from error

    session_path = "/tmp/instaloader-session"

    with open(session_path, "wb") as session_file:
        session_file.write(session_data)

    loader = instaloader.Instaloader()

    try:
        loader.load_session_from_file(
            username=INSTAGRAM_USERNAME,
            filename=session_path
        )
    except Exception as error:
        raise InstagramSetupError(
            "Could not load the Instagram session; check INSTAGRAM_USERNAME "
            "and the session value"
        ) from error

    logged_in_as = loader.test_login()

    if logged_in_as != INSTAGRAM_USERNAME:
        raise InstagramSetupError(
            "Instagram session is invalid/expired or INSTAGRAM_USERNAME "
            "does not match the account"
        )

    profile = instaloader.Profile.from_username(
        loader.context,
        username
    )

    return profile.profile_pic_url


def send_document(chat_id, image_url, username):
    response = requests.get(
        image_url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )

    response.raise_for_status()

    telegram_request(
        "sendDocument",
        data={"chat_id": chat_id},
        files={
            "document": (
                f"{username}_profile.jpg",
                response.content,
                "image/jpeg"
            )
        }
    )


def process_update(update):
    message = update.get("message")

    if not message or "text" not in message:
        return

    chat_id = message["chat"]["id"]
    text = message["text"].strip()

    if text.startswith("/start"):
        send_message(
            chat_id,
            "Instagram Profile Downloader\n\n"
            "Send an Instagram username or profile link."
        )
        return

    username = None
    stage = "validating the username"

    try:
        username = extract_username(text)

        send_message(chat_id, f"Downloading @{username} ...")

        stage = "fetching the Instagram profile picture"
        image_url = get_profile_picture(username)

        stage = "sending the picture to Telegram"
        send_document(chat_id, image_url, username)

        send_message(
            chat_id,
            f"Successfully downloaded @{username} profile picture."
        )

    except ValueError:
        send_message(chat_id, "Invalid Instagram username or profile link.")

    except Exception as error:
        logger.exception(
            "Profile download failed at stage=%s username=%s",
            stage,
            username or "unknown"
        )

        if isinstance(error, InstagramSetupError):
            send_message(
                chat_id,
                "Bot setup error: the Instagram session configuration is "
                "missing, invalid, or expired. Check INSTAGRAM_USERNAME and "
                "INSTAGRAM_SESSION_B64 in Vercel environment variables, then "
                "redeploy. Do not share these secrets."
            )
        else:
            send_message(
                chat_id,
                "Download failed while " + stage + ". Check the Vercel "
                "function logs for the detailed error. Instagram may have "
                "restricted this request, or Telegram may have rejected the "
                "image."
            )


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Instagram Bot is running")

    def do_POST(self):
        if self.path != "/api/webhook":
            self.send_response(404)
            self.end_headers()
            return

        received_secret = self.headers.get(
            "X-Telegram-Bot-Api-Secret-Token", ""
        )

        if not hmac.compare_digest(received_secret, WEBHOOK_SECRET):
            self.send_response(403)
            self.end_headers()
            return

        try:
            length = int(self.headers.get("Content-Length", 0))

            if length <= 0 or length > 1024 * 1024:
                self.send_response(400)
                self.end_headers()
                return

            body = self.rfile.read(length)
            update = json.loads(body)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

            process_update(update)

        except Exception:
            logger.exception("Webhook processing error")
