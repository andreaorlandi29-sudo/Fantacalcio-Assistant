"""
Scommesse "esterne": segnalazioni di giocatori a basso costo/buon potenziale
raccolte da una ricerca web su fonti generaliste (Fantacalcio.it, TuttoMercatoWeb,
Fanpage.it, Skuola.net, ecc.) — DIVERSE dai pareri dei 3 creator di riferimento
(vedi bot/pareri_store.py), che sono inseriti solo quando l'utente li riporta.

Non e' una raccolta automatica e continua: e' un elenco raccolto UNA TANTUM
(ricerca del 27/08/2026, vedi SEED sotto) + la possibilita' di aggiungerne
altre quando l'utente segnala una nuova fonte in chat. Le notizie di mercato
cambiano in fretta: il bot deve sempre dire quando e' stata raccolta l'info.

Storage: stessa infrastruttura Redis di rosa/pareri (bot/redis_conn.py).
  {"scommesse": [{"giocatore","squadra","ruolo","motivo","fonti":[...],
                   "aggiunto_il"}]}
"""
import datetime
import json

from . import redis_conn

KEY = "scommesse_esterne:v1"

# Le 12 scommesse con doppia conferma (2+ fonti indipendenti) trovate nella
# ricerca del 27/08/2026, gia' incrociate col dataset quotazioni (tutte
# confermate quotate 5-12 crediti).
SEED = [
    {"giocatore": "Kaiki", "squadra": "COM", "ruolo": "ds/e", "quotazione": 7,
     "motivo": "Candidato a giocare con continuità sulla fascia del Como.",
     "fonti": ["Fanpage.it", "Skuola.net"]},
    {"giocatore": "Doekhi", "squadra": "LAZ", "ruolo": "dc", "quotazione": 8,
     "motivo": "Centrale arrivato quest'estate, con \"il vizio del gol\".",
     "fonti": ["Fantacalcio.it", "Skuola.net"]},
    {"giocatore": "Rensch", "squadra": "ROM", "ruolo": "b/dd/e", "quotazione": 6,
     "motivo": "Può trovare più spazio nella Roma di Gasperini.",
     "fonti": ["Fantacalcio.it", "Skuola.net"]},
    {"giocatore": "Marcandalli", "squadra": "GEN", "ruolo": "dc", "quotazione": 6,
     "motivo": "Continuità di impiego + pericolosità aerea, bene in preparazione.",
     "fonti": ["Fantacalcio.it", "Fanpage.it"]},
    {"giocatore": "Samardzic", "squadra": "ATA", "ruolo": "c/t", "quotazione": 12,
     "motivo": "Finalmente nel ruolo che preferisce Sarri, qualità superiore alla quotazione.",
     "fonti": ["Fantacalcio.it", "Skuola.net"]},
    {"giocatore": "Liberali", "squadra": "COM", "ruolo": "t", "quotazione": 5,
     "motivo": "Fabregas lo utilizzerà con continuità, talento sopra la media del prezzo.",
     "fonti": ["Fantacalcio.it", "Fanpage.it"]},
    {"giocatore": "Amondarain", "squadra": "BOL", "ruolo": "m/c", "quotazione": 6,
     "motivo": "Buon prospetto con esperienza internazionale, low cost.",
     "fonti": ["Fantacalcio.it", "Fanpage.it"]},
    {"giocatore": "Cacciamani", "squadra": "TOR", "ruolo": "e/w", "quotazione": 6,
     "motivo": "Già lavorato con Abate in precedenza, favorito per spazio.",
     "fonti": ["Fantacalcio.it", "Fanpage.it"]},
    {"giocatore": "Alajbegovic", "squadra": "JUV", "ruolo": "w/t", "quotazione": 12,
     "motivo": "Giovane di prospetto, può incidere anche subentrando.",
     "fonti": ["Fantacalcio.it", "Fanpage.it"]},
    {"giocatore": "Geubbels", "squadra": "LEC", "ruolo": "pc", "quotazione": 8,
     "motivo": "Rigorista designato del Lecce.",
     "fonti": ["Fantacalcio.it", "Skuola.net"]},
    {"giocatore": "Romero", "squadra": "PAR", "ruolo": "pc", "quotazione": 10,
     "motivo": "Investimento importante del club, atteso a produrre gol.",
     "fonti": ["Fantacalcio.it", "Fanpage.it"]},
    {"giocatore": "Ghedjemis", "squadra": "FRO", "ruolo": "w/a", "quotazione": 10,
     "motivo": "15 gol + 3 assist in Serie B lo scorso anno, ha trascinato il Frosinone in A.",
     "fonti": ["TuttoMercatoWeb", "Skuola.net"]},
]
SEED_RACCOLTA_IL = "2026-08-27"


def _conn():
    return redis_conn.get_client()


def carica() -> dict:
    d = _conn().get(KEY)
    if not d:
        return {"scommesse": []}
    return json.loads(d)


def _salva(stato: dict) -> None:
    _conn().set(KEY, json.dumps(stato, ensure_ascii=False))


def registra(giocatore: str, squadra: str, ruolo: str, motivo: str,
             fonti: list[str] | None = None) -> dict:
    stato = carica()
    voce = {
        "giocatore": giocatore.strip(), "squadra": squadra.strip().upper(),
        "ruolo": ruolo.strip().lower(), "quotazione": None,
        "motivo": motivo.strip(), "fonti": fonti or [],
        "aggiunto_il": datetime.date.today().isoformat(),
    }
    stato["scommesse"].append(voce)
    _salva(stato)
    return {"registrato": voce, "totale": len(stato["scommesse"])}


def cerca(giocatore: str) -> list[dict]:
    q = giocatore.strip().lower()
    return [s for s in carica()["scommesse"] if q in s["giocatore"].lower()]


def elenco() -> list[dict]:
    return carica()["scommesse"]


def carica_seed() -> dict:
    """Carica le 12 scommesse iniziali, una volta sola (idempotente: salta
    quelle già presenti per nome+squadra)."""
    stato = carica()
    esistenti = {(s["giocatore"].lower(), s["squadra"]) for s in stato["scommesse"]}
    aggiunte = []
    for voce in SEED:
        chiave = (voce["giocatore"].lower(), voce["squadra"])
        if chiave in esistenti:
            continue
        nuova = dict(voce)
        nuova["aggiunto_il"] = SEED_RACCOLTA_IL
        stato["scommesse"].append(nuova)
        aggiunte.append(nuova["giocatore"])
    if aggiunte:
        _salva(stato)
    return {"aggiunte": aggiunte, "gia_presenti": len(SEED) - len(aggiunte),
            "totale_in_archivio": len(stato["scommesse"])}
