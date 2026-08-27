"""
Pareri dei creator di riferimento (Carmine Special / CarmySpecial, Re Costa,
il Profeta), inseriti MANUALMENTE dall'utente — non c'e' nessuna raccolta
automatica: i loro contenuti reali sono video (YouTube/Twitch) o social, non
testo scrapabile, e in ogni caso i Termini di Servizio di Fantacalcio.it
vietano lo scraping delle loro rubriche (ferme dal 2024) senza autorizzazione.

Quando l'utente sente/legge un parere e me lo riporta in chat ("Carmy dice
che Retegui e' da prendere fino a 90"), il bot lo registra qui; da quel
momento in poi viene richiamato quando si parla di quel giocatore.

Storage: stessa infrastruttura Redis della rosa (bot/redis_conn.py), chiave
dedicata, cosi' sopravvive ai redeploy. Un solo documento JSON:
  {"pareri": [{"giocatore","creator","parere","aggiunto_il"}, ...]}
"""
import datetime
import json

from . import redis_conn

KEY = "pareri_creator:v1"
CREATOR_NOTI = ["Carmine Special", "CarmySpecial", "Re Costa", "Recosta", "il Profeta"]


def _conn():
    return redis_conn.get_client()


def carica() -> dict:
    d = _conn().get(KEY)
    if not d:
        return {"pareri": []}
    return json.loads(d)


def _salva(stato: dict) -> None:
    _conn().set(KEY, json.dumps(stato, ensure_ascii=False))


def registra(giocatore: str, creator: str, parere: str) -> dict:
    stato = carica()
    voce = {
        "giocatore": giocatore.strip(),
        "creator": creator.strip(),
        "parere": parere.strip(),
        "aggiunto_il": datetime.date.today().isoformat(),
    }
    stato["pareri"].append(voce)
    _salva(stato)
    return {"registrato": voce, "totale_pareri": len(stato["pareri"])}


def cerca(giocatore: str) -> list[dict]:
    q = giocatore.strip().lower()
    return [p for p in carica()["pareri"] if q in p["giocatore"].lower()]


def elenco() -> list[dict]:
    return carica()["pareri"]


def rimuovi_ultimo(giocatore: str | None = None) -> dict:
    stato = carica()
    if not stato["pareri"]:
        return {"errore": "Nessun parere registrato da rimuovere."}
    if giocatore:
        cand = [i for i, p in enumerate(stato["pareri"])
                if giocatore.strip().lower() in p["giocatore"].lower()]
        if not cand:
            return {"errore": f"Nessun parere trovato per '{giocatore}'."}
        idx = cand[-1]
    else:
        idx = len(stato["pareri"]) - 1
    rimosso = stato["pareri"].pop(idx)
    _salva(stato)
    return {"rimosso": rimosso}
