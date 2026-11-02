import os
import json
import urllib.request
import urllib.parse

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]

WEBHOOK_URL = "https://instagram-profile-bot-five.vercel.app/api/webhook"


def handler(request):
    if request.method != "GET":
        return {
            "statusCode": 405,
            "body": "Method not allowed"
        }

    params = urllib.parse.urlencode({
        "url": WEBHOOK_URL,
        "secret_token": WEBHOOK_SECRET
    }).encode()

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"

    try:
        req = urllib.request.Request(url, data=params)

        with urllib.request.urlopen(req, timeout=20) as response:
            result = json.loads(response.read())

        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }

    except Exception as error:
        return {
            "statusCode": 500,
            "body": str(error)
        }
