"""
Stato rosa persistente durante l'asta, su storage SEPARATO dal codice del bot
(Render Key Value / Redis), cosi' i redeploy del bot non lo cancellano.

La rosa e' un unico documento JSON salvato sotto una sola chiave Redis:
  {
    "budget_totale": 500,
    "acquisti": [
      {"nome","player_id","squadra","ruolo_mantra","crediti","reparto"}, ...
    ]
  }

Connessione: variabile d'ambiente REDIS_URL (connection string del Render
Key Value). Se manca, le funzioni sollevano un errore chiaro e il resto del
bot continua a funzionare (i tool rosa restituiscono un messaggio utile).

Per i test locali senza Render: si puo' iniettare un client redis fittizio
tramite set_client() (vedi bot/... test), senza toccare il codice di produzione.
"""
import csv
import json
import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATASET = REPO / "data" / "dataset_unificato.csv"

KEY = "rosa:v1"
BUDGET_DEFAULT = 500

# mappa ruolo Mantra -> reparto (per il conteggio degli slot)
RUOLO_REPARTO = {
    "por": "portieri",
    "dc": "difensori", "dd": "difensori", "ds": "difensori", "b": "difensori",
    "m": "centrocampisti", "c": "centrocampisti",
    "e": "esterni", "w": "esterni",
    "t": "attacco", "a": "attacco", "pc": "attacco",
}
# target (min, max) per reparto, dal CLAUDE.md (modulo difesa a 3)
TARGET = {
    "portieri": (3, 3),
    "difensori": (6, 7),
    "centrocampisti": (5, 6),
    "esterni": (4, 5),
    "attacco": (3, 4),
}
ORDINE = ["portieri", "difensori", "centrocampisti", "esterni", "attacco"]

_client = None  # override per i test (fakeredis)


def set_client(client):
    """Inietta un client redis (per i test). In produzione non si usa."""
    global _client
    _client = client


def _conn():
    global _client
    if _client is not None:
        return _client
    if os.environ.get("ROSA_FAKE"):          # solo per test locali
        import fakeredis
        _client = fakeredis.FakeStrictRedis(decode_responses=True)
        return _client
    url = os.environ.get("REDIS_URL")
    if not url:
        raise RuntimeError(
            "Storage rosa non configurato: manca la variabile d'ambiente REDIS_URL. "
            "Collega un Render Key Value (vedi docs/STORAGE_ROSA.md).")
    import redis  # import lazy: il bot parte anche senza redis installato/config
    _client = redis.from_url(url, decode_responses=True)
    return _client


def _int(v) -> int:
    return int(round(float(v)))


# ----------------------------------------------------------------- dataset
def _trova_giocatore(nome: str) -> list[dict]:
    q = nome.strip().lower()
    with open(DATASET, encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if q in r["nome"].lower()]


def reparto_di(ruolo_mantra: str) -> str:
    primo = (ruolo_mantra or "").split("/")[0].strip().lower()
    return RUOLO_REPARTO.get(primo, "sconosciuto")


def _candidati(match: list[dict]) -> list[str]:
    return [f'{m["nome"]} ({m["squadra"]}, {m["ruolo_mantra"]})' for m in match[:8]]


# ----------------------------------------------------------------- storage
def carica() -> dict:
    d = _conn().get(KEY)
    if not d:
        return {"budget_totale": BUDGET_DEFAULT, "acquisti": []}
    return json.loads(d)


def _salva(stato: dict) -> None:
    _conn().set(KEY, json.dumps(stato, ensure_ascii=False))


def _voce(nome: str, crediti, g: dict | None) -> dict:
    if g:
        return {"nome": g["nome"], "player_id": g["player_id"], "squadra": g["squadra"],
                "ruolo_mantra": g["ruolo_mantra"], "crediti": _int(crediti),
                "reparto": reparto_di(g["ruolo_mantra"])}
    return {"nome": nome.strip(), "player_id": "", "squadra": "", "ruolo_mantra": "?",
            "crediti": _int(crediti), "reparto": "sconosciuto"}


def registra(nome: str, crediti) -> dict:
    match = _trova_giocatore(nome)
    if len(match) > 1:
        return {"conferma_necessaria": True, "candidati": _candidati(match),
                "messaggio": f"Piu' giocatori corrispondono a '{nome}': chiedi quale."}
    stato = carica()
    voce = _voce(nome, crediti, match[0] if match else None)
    stato["acquisti"].append(voce)
    _salva(stato)
    return {"registrato": voce, "nota": None if match else
            f"'{nome}' non trovato nel dataset: registrato senza ruolo.",
            "stato_rosa": stato_rosa(stato)}


def correggi(nome: str | None = None, nuovo_prezzo=None, nuovo_nome: str | None = None) -> dict:
    stato = carica()
    if not stato["acquisti"]:
        return {"errore": "Nessun acquisto registrato da correggere."}
    idx = len(stato["acquisti"]) - 1  # default: l'ultimo
    if nome:
        cand = [i for i, v in enumerate(stato["acquisti"])
                if nome.strip().lower() in v["nome"].lower()]
        if not cand:
            return {"errore": f"'{nome}' non risulta tra gli acquisti registrati."}
        idx = cand[-1]
    voce = dict(stato["acquisti"][idx])
    if nuovo_nome:
        m = _trova_giocatore(nuovo_nome)
        if len(m) > 1:
            return {"conferma_necessaria": True, "candidati": _candidati(m)}
        voce = _voce(nuovo_nome, voce["crediti"], m[0] if m else None)
    if nuovo_prezzo is not None:
        voce["crediti"] = _int(nuovo_prezzo)
    stato["acquisti"][idx] = voce
    _salva(stato)
    return {"corretto": voce, "stato_rosa": stato_rosa(stato)}


def annulla_ultimo() -> dict:
    stato = carica()
    if not stato["acquisti"]:
        return {"errore": "Nessun acquisto da annullare."}
    v = stato["acquisti"].pop()
    _salva(stato)
    return {"annullato": v, "stato_rosa": stato_rosa(stato)}


def reset() -> dict:
    _conn().delete(KEY)
    return {"ok": True, "messaggio": "Rosa azzerata: 0 acquisti, budget 500 di nuovo pieno."}


# ----------------------------------------------------------------- stato
def stato_rosa(stato: dict | None = None) -> dict:
    stato = stato if stato is not None else carica()
    budget = stato.get("budget_totale", BUDGET_DEFAULT)
    spesa = sum(v["crediti"] for v in stato["acquisti"])
    reparti = []
    contati = {r: [] for r in ORDINE}
    senza = []
    for v in stato["acquisti"]:
        r = v.get("reparto", "sconosciuto")
        (contati[r] if r in contati else senza).append(v)
    for r in ORDINE:
        presi = len(contati[r])
        tmin, tmax = TARGET[r]
        reparti.append({
            "reparto": r, "presi": presi, "target_min": tmin, "target_max": tmax,
            "mancanti_al_minimo": max(0, tmin - presi),
            "pieno": presi >= tmax,          # non prendere altri qui
            "minimo_raggiunto": presi >= tmin,
            "giocatori": [{"nome": g["nome"], "crediti": g["crediti"],
                           "ruolo_mantra": g["ruolo_mantra"], "squadra": g["squadra"]}
                          for g in contati[r]],
        })
    return {
        "budget_totale": budget, "crediti_spesi": spesa,
        "crediti_residui": budget - spesa, "num_giocatori": len(stato["acquisti"]),
        "reparti": reparti,
        "senza_reparto": [{"nome": g["nome"], "crediti": g["crediti"]} for g in senza],
    }
