"""
Server webhook per il bot Telegram (per hosting su Render Web Service, free).

A differenza del polling (bot/telegram_bot.py), qui e' Telegram a inviarci i
messaggi via HTTP POST su un endpoint. Adatto a un Web Service che dorme e si
risveglia su richiesta.

Sicurezza: Telegram invia, ad ogni chiamata, l'header
  X-Telegram-Bot-Api-Secret-Token
con il valore che impostiamo in setWebhook. Verifichiamo che coincida con
WEBHOOK_SECRET: cosi' l'endpoint non e' azionabile da chiunque conosca l'URL.

Auto-registrazione: all'avvio, se conosciamo l'URL pubblico (RENDER_EXTERNAL_URL
fornito da Render, oppure WEBHOOK_URL), il server registra da solo il webhook su
Telegram. Non serve quindi alcuna chiamata manuale (ma resta possibile: vedi
bot/set_webhook.py).

Avvio in produzione (Render):
  gunicorn bot.webhook:app --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT

Variabili d'ambiente:
  TELEGRAM_BOT_TOKEN   (obbligatoria)
  ANTHROPIC_API_KEY    (obbligatoria)
  WEBHOOK_SECRET       (consigliata) stringa casuale per verificare le richieste
  RENDER_EXTERNAL_URL  (fornita da Render) o WEBHOOK_URL per l'auto-registrazione
  CLAUDE_MODEL, TELEGRAM_ALLOWED_USER_ID  (opzionali, come nel polling)
"""
import os
import threading

from flask import Flask, request, abort

from . import telegram_bot as tb  # riusa _gestisci, _tg, _invia, ecc.

app = Flask(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
SECRET = os.environ.get("WEBHOOK_SECRET", "")
PATH = "/webhook"


@app.get("/")
def health():
    """Health check: utile per verificare a mano che il servizio sia su."""
    return "Fantacalcio Mantra bot: attivo.", 200


@app.post(PATH)
def webhook():
    # verifica che la richiesta arrivi davvero da Telegram
    if SECRET and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET:
        abort(403)
    update = request.get_json(silent=True) or {}
    msg = update.get("message")
    if msg:
        # elabora in un thread e rispondi subito 200: cosi' Telegram non va in
        # timeout/retry mentre Claude ragiona (evita risposte doppie)
        threading.Thread(target=tb._gestisci, args=(TOKEN, msg), daemon=True).start()
    return "ok", 200


def _url_pubblico() -> str:
    url = os.environ.get("WEBHOOK_URL") or os.environ.get("RENDER_EXTERNAL_URL", "")
    return url.rstrip("/")


def registra_webhook() -> str:
    """Registra il webhook su Telegram (chiamata a setWebhook). Idempotente."""
    base = _url_pubblico()
    if not (TOKEN and base):
        return "auto-registrazione saltata (manca URL pubblico o token)"
    params = {"url": base + PATH, "allowed_updates": ["message"]}
    if SECRET:
        params["secret_token"] = SECRET
    res = tb._tg(TOKEN, "setWebhook", **params)
    return f"setWebhook -> {res.get('description', res)}"


# auto-registrazione all'avvio (una volta per processo)
try:
    print(registra_webhook(), flush=True)
except Exception as e:  # non impedire l'avvio del server se Telegram non risponde
    print("registrazione webhook fallita:", e, flush=True)


if __name__ == "__main__":
    # solo per prova locale: in produzione si usa gunicorn
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
