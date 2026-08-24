"""
Bot Telegram (solo testo) che inoltra i messaggi a Claude via API.

Avvio:  python3 -m bot.telegram_bot

Variabili d'ambiente richieste (NON hardcodare qui):
  TELEGRAM_BOT_TOKEN   token del bot (da @BotFather)
  ANTHROPIC_API_KEY    chiave API Anthropic
Opzionali:
  CLAUDE_MODEL             modello (default claude-opus-5)
  TELEGRAM_ALLOWED_USER_ID se impostata, il bot risponde solo a quell'ID utente

Usa long-polling (getUpdates): nessun webhook, funziona in locale.
"""
import os
import sys
import time
from datetime import datetime

import requests


def _log(*a):
    print(datetime.now().strftime("%H:%M:%S"), *a, flush=True)

from . import agent

API = "https://api.telegram.org/bot{token}/{method}"
# storico conversazione per chat (in memoria, si azzera al riavvio)
_storici: dict[int, list] = {}
_MAX_STORICO = 12  # messaggi tenuti per chat (6 scambi circa)


def _tg(token, method, tentativi=4, **params):
    """Chiama l'API Telegram con retry su errori di rete/proxy (connection reset)."""
    ultimo = None
    for i in range(tentativi):
        try:
            r = requests.post(API.format(token=token, method=method),
                              json=params, timeout=75)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            ultimo = e
            time.sleep(min(2 ** i, 8))
    raise ultimo


def _invia(token, chat_id, testo):
    # niente parse_mode: testo semplice, evita errori di escaping Markdown
    for i in range(0, len(testo), 3900):          # Telegram: max ~4096 char/msg
        _tg(token, "sendMessage", chat_id=chat_id, text=testo[i:i + 3900])


def _gestisci(token, msg):
    chat_id = msg["chat"]["id"]
    user_id = msg.get("from", {}).get("id")
    testo = (msg.get("text") or "").strip()
    if not testo:
        return

    ammesso = os.environ.get("TELEGRAM_ALLOWED_USER_ID")
    if ammesso and str(user_id) != str(ammesso):
        _invia(token, chat_id, "Bot privato: non sei autorizzato.")
        return

    if testo in ("/start", "/help"):
        _invia(token, chat_id,
               "Ciao! Sono il tuo assistente Fantacalcio Mantra.\n"
               "Chiedimi pure in linguaggio naturale, es.:\n"
               "• \"i migliori 10 difensori\"\n"
               "• \"5 scommesse per il centrocampo sotto i 10 crediti\"\n"
               "• \"meglio Bastoni o Gatti?\"")
        return

    _log(f"IN  chat={chat_id} user={user_id}: {testo!r}")
    storico = _storici.get(chat_id, [])
    t0 = time.time()
    try:
        risposta = agent.rispondi(testo, storico=storico)
    except Exception as e:
        _log(f"ERR {type(e).__name__}: {e}")
        _invia(token, chat_id, f"Errore nell'elaborazione: {type(e).__name__}: {e}")
        return
    _log(f"OUT chat={chat_id} ({time.time()-t0:.1f}s, {len(risposta)} char)")

    # aggiorna storico (troncato)
    storico = storico + [{"role": "user", "content": testo},
                         {"role": "assistant", "content": risposta}]
    _storici[chat_id] = storico[-_MAX_STORICO:]
    _invia(token, chat_id, risposta)


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        sys.exit("ERRORE: manca TELEGRAM_BOT_TOKEN nell'ambiente.")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ERRORE: manca ANTHROPIC_API_KEY nell'ambiente.")

    me = _tg(token, "getMe")["result"]
    print(f"Bot avviato: @{me.get('username')} (modello {agent.MODEL}). Ctrl+C per fermare.")
    offset = None
    while True:
        try:
            # SHORT polling: chiamate brevi (timeout=0). In questo ambiente il
            # proxy resetta le connessioni long-poll, mentre le chiamate brevi
            # funzionano; una piccola pausa evita di martellare l'API.
            upd = _tg(token, "getUpdates", timeout=0, offset=offset)
        except requests.RequestException as e:
            _log("rete getUpdates:", e); time.sleep(3); continue
        if not upd.get("result"):
            time.sleep(2)
        for u in upd.get("result", []):
            offset = u["update_id"] + 1
            if "message" in u:
                try:
                    _gestisci(token, u["message"])
                except Exception as e:            # un errore su un messaggio non ferma il bot
                    _log(f"errore gestione update {u['update_id']}: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
