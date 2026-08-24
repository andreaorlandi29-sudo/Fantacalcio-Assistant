"""
Gestione manuale del webhook Telegram (in alternativa all'auto-registrazione
che avviene all'avvio di bot/webhook.py).

Uso:
  python3 -m bot.set_webhook set   https://tuo-servizio.onrender.com
  python3 -m bot.set_webhook info
  python3 -m bot.set_webhook delete   # torna al polling / rimuove il webhook

Legge TELEGRAM_BOT_TOKEN e WEBHOOK_SECRET dall'ambiente.
"""
import os
import sys

from . import telegram_bot as tb

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
SECRET = os.environ.get("WEBHOOK_SECRET", "")


def main():
    if not TOKEN:
        sys.exit("manca TELEGRAM_BOT_TOKEN")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "info"

    if cmd == "set":
        if len(sys.argv) < 3:
            sys.exit("uso: set <BASE_URL>  (es. https://xxx.onrender.com)")
        base = sys.argv[2].rstrip("/")
        params = {"url": base + "/webhook", "allowed_updates": ["message"]}
        if SECRET:
            params["secret_token"] = SECRET
        print(tb._tg(TOKEN, "setWebhook", **params))
    elif cmd == "delete":
        print(tb._tg(TOKEN, "deleteWebhook"))
    else:  # info
        print(tb._tg(TOKEN, "getWebhookInfo"))


if __name__ == "__main__":
    main()
