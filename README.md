# Instagram Profile Downloader Bot

This Telegram bot downloads the profile picture for an Instagram username or profile link.

## Vercel environment variables

Set these in **Vercel → Project → Settings → Environment Variables**, then redeploy:

- `BOT_TOKEN`: Telegram bot token.
- `WEBHOOK_SECRET`: the secret token configured for the Telegram webhook.
- `INSTAGRAM_SESSION_B64`: the Base64-encoded Instaloader session file.
- `INSTAGRAM_USERNAME`: the Instagram username for the account that owns that session. It defaults to `aryatrgrn` if omitted; set it to the correct account if you used a different one.
- `SETUP_KEY`: key used to protect the webhook setup endpoint.

Keep `BOT_TOKEN`, `WEBHOOK_SECRET`, `INSTAGRAM_SESSION_B64`, and `SETUP_KEY` private. Do not post them in issues, chats, or logs. If a valid session still fails because Instagram is restricting requests from the deployment, the bot cannot guarantee access; do not try to evade Instagram's restrictions.

## Diagnosing download failures

The bot now distinguishes a missing/invalid Instagram session configuration from failures fetching or sending the image. For other errors, open **Vercel → Project → Logs** (or the function's runtime logs) and inspect the `Profile download failed` entry. It records the failing stage and exception without logging the session value or Telegram token.
