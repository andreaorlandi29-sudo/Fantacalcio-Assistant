"""
Scommesse "esterne": segnalazioni di giocatori a basso costo/buon potenziale
raccolte da ricerche web (fonti generaliste come Fantacalcio.it, TuttoMercatoWeb,
Fanpage.it, Skuola.net, ma anche fonti piu' di nicchia come SOS Fanta,
PazziDiFanta, Fantamaster) — DIVERSE dai pareri dei 3 creator di riferimento
(vedi bot/pareri_store.py), che sono inseriti solo quando l'utente li riporta.

Non e' una raccolta automatica e continua: sono elenchi raccolti UNA TANTUM
(vedi SEED e SEED_2 sotto) + la possibilita' di aggiungerne altre quando
l'utente segnala una nuova fonte in chat. Le notizie di mercato cambiano in
fretta: il bot deve sempre dire quando e' stata raccolta l'info.

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

# Secondo batch, da fonti meno generaliste/di nicchia (SOS Fanta, PazziDiFanta,
# Fantamaster), ricerca del 27/08/2026. A differenza del primo batch, qui la
# maggior parte dei nomi ha UNA sola fonte (fa eccezione Adzic, confermato da
# due fonti indipendenti): il campo "fonti" riflette onestamente quante ce ne
# sono per ciascuno. Tutti incrociati col dataset quotazioni (3-12 crediti).
# Esclusi da questo batch: "Atta" (Fiorentina, Q16/FVM86 - fascia troppo alta
# per una vera "chicca" e con incongruenza di squadra rispetto alla fonte, che
# lo dava all'Udinese) e i nomi non trovati nel dataset (Angori, V. Carboni,
# Tramoni) - da verificare manualmente se l'utente ha conferme dirette.
SEED_2 = [
    {"giocatore": "Ramon", "squadra": "COM", "ruolo": "dc", "quotazione": 10,
     "motivo": "Centrale spagnolo, candidato titolare nella difesa del Como.",
     "fonti": ["SOS Fanta"]},
    {"giocatore": "Ghilardi", "squadra": "ROM", "ruolo": "dc", "quotazione": 4,
     "motivo": "Centrale di scorta/rotazione a basso costo nella Roma di Gasperini.",
     "fonti": ["SOS Fanta"]},
    {"giocatore": "Provstgaard", "squadra": "LAZ", "ruolo": "dc", "quotazione": 3,
     "motivo": "Centrale danese, possibile alternativa economica in una difesa Lazio con poche certezze.",
     "fonti": ["SOS Fanta"]},
    {"giocatore": "Palma", "squadra": "UDI", "ruolo": "dc", "quotazione": 3,
     "motivo": "Giovane centrale dell'Udinese, ancora acerbo ma a costo minimo.",
     "fonti": ["SOS Fanta"]},
    {"giocatore": "Puczka", "squadra": "GEN", "ruolo": "ds/e", "quotazione": 2,
     "motivo": "Esterno basso del Genoa, profilo economico per completare la rosa.",
     "fonti": ["Fantamaster"]},
    {"giocatore": "Diouf", "squadra": "INT", "ruolo": "e/c", "quotazione": 10,
     "motivo": "Trova continuita' con Chivu dopo una stagione opaca; NB: la fonte lo indicava genericamente"
               " senza citare Chivu come tecnico Roma, ma Chivu allena l'Inter: squadra confermata dal dataset.",
     "fonti": ["SOS Fanta"]},
    {"giocatore": "Oulai", "squadra": "FIO", "ruolo": "m/c", "quotazione": 7,
     "motivo": "Centrocampista ancora senza storico in Serie A, scommessa di prospettiva.",
     "fonti": ["SOS Fanta"]},
    {"giocatore": "Adzic", "squadra": "SAS", "ruolo": "c/t", "quotazione": 5,
     "motivo": "Buona duttilita' tattica, affidabilita' e impatto sui calci piazzati del Sassuolo.",
     "fonti": ["SOS Fanta", "Fantamaster"]},
    {"giocatore": "Mendy P.", "squadra": "CAG", "ruolo": "pc", "quotazione": 3,
     "motivo": "Attaccante low cost del Cagliari, ancora da valutare ma prezzo minimo.",
     "fonti": ["SOS Fanta"]},
    {"giocatore": "Cutrone", "squadra": "MON", "ruolo": "pc", "quotazione": 8,
     "motivo": "Attaccante esperto, cambio squadra al Monza dove puo' avere spazio da titolare.",
     "fonti": ["SOS Fanta"]},
    {"giocatore": "Adams A.", "squadra": "VEN", "ruolo": "pc", "quotazione": 11,
     "motivo": "Centravanti nigeriano, atteso protagonista dell'attacco del Venezia neopromosso.",
     "fonti": ["SOS Fanta"]},
    {"giocatore": "Ekkelenkamp", "squadra": "UDI", "ruolo": "c/t", "quotazione": 11,
     "motivo": "Centrocampista offensivo con buona qualita' rispetto al costo nell'Udinese.",
     "fonti": ["SOS Fanta"]},
    {"giocatore": "Sorensen O.", "squadra": "PAR", "ruolo": "c", "quotazione": 3,
     "motivo": "Segnalato come possibile rigorista del Parma, costo minimo.",
     "fonti": ["SOS Fanta"]},
    {"giocatore": "Fazzini", "squadra": "CAG", "ruolo": "c/t", "quotazione": 8,
     "motivo": "Centrocampista offensivo, cambio squadra al Cagliari dopo stagione deludente all'Empoli;"
               " ATTENZIONE rischio fisico, 166 giorni ai box nelle ultime due stagioni secondo la fonte.",
     "fonti": ["PazziDiFanta"]},
    {"giocatore": "Valdepenas", "squadra": "FIO", "ruolo": "ds/dc", "quotazione": 7,
     "motivo": "Terzino classe 2006 ex Real Madrid, senza storico in Serie A: scommessa di prospettiva.",
     "fonti": ["PazziDiFanta"]},
    {"giocatore": "Oristanio", "squadra": "TOR", "ruolo": "w/t", "quotazione": 7,
     "motivo": "Cambio squadra al Torino, ruolo piu' adatto alle sue caratteristiche nel modulo di Abate.",
     "fonti": ["PazziDiFanta"]},
    {"giocatore": "Bella-Kotchap", "squadra": "VEN", "ruolo": "dc", "quotazione": 6,
     "motivo": "Centrale tedesco, cambio squadra al Venezia dopo una stagione difficile a Verona.",
     "fonti": ["PazziDiFanta"]},
    {"giocatore": "Calò", "squadra": "FRO", "ruolo": "m/c", "quotazione": 8,
     "motivo": "Arriva dalla Serie B con 10 gol e 15 assist, candidato a rigori e piazzati del Frosinone;"
               " storico Serie B non ancora nel dataset di Serie A.",
     "fonti": ["PazziDiFanta"]},
    {"giocatore": "Mangas", "squadra": "MON", "ruolo": "ds/e", "quotazione": 6,
     "motivo": "Giochera' alto nel 3-5-2 del Monza di Juric.",
     "fonti": ["Fantamaster"]},
    {"giocatore": "Viery", "squadra": "FIO", "ruolo": "ds/dc", "quotazione": 7,
     "motivo": "Pronto a convincere Grosso per una maglia da titolare in una difesa Fiorentina con poche certezze.",
     "fonti": ["Fantamaster"]},
    {"giocatore": "Romano", "squadra": "CAG", "ruolo": "m/c", "quotazione": 8,
     "motivo": "Ottima pre-season, possibile titolare con Pisacane.",
     "fonti": ["Fantamaster"]},
    {"giocatore": "Hasa", "squadra": "FRO", "ruolo": "c/t", "quotazione": 3,
     "motivo": "Scommessa intrigante a costo minimo nel centrocampo del Frosinone.",
     "fonti": ["Fantamaster"]},
    {"giocatore": "Ellertsson", "squadra": "GEN", "ruolo": "e/c", "quotazione": 7,
     "motivo": "Duttilita' tattica che garantisce affidabilita' e costanza di impiego nel Genoa.",
     "fonti": ["Fantamaster"]},
    {"giocatore": "Kevin Carlos", "squadra": "CAG", "ruolo": "pc", "quotazione": 12,
     "motivo": "Nuovo acquisto del Cagliari, ancora tutto da scoprire ma prezzo contenuto.",
     "fonti": ["Fantamaster"]},
    {"giocatore": "Bowie", "squadra": "SAS", "ruolo": "pc", "quotazione": 9,
     "motivo": "Pronto a ereditare il posto da titolare di Pinamonti (passato alla Lazio) nel Sassuolo.",
     "fonti": ["Fantamaster"]},
]
SEED_2_RACCOLTA_IL = "2026-08-27"

SEED_BATCHES = [(SEED, SEED_RACCOLTA_IL), (SEED_2, SEED_2_RACCOLTA_IL)]


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
    """Carica tutti i batch SEED (SEED + SEED_2, ...), una volta sola per voce
    (idempotente: salta quelle già presenti per nome+squadra, anche fra batch
    diversi)."""
    stato = carica()
    esistenti = {(s["giocatore"].lower(), s["squadra"]) for s in stato["scommesse"]}
    aggiunte = []
    totale_seed = 0
    for batch, raccolta_il in SEED_BATCHES:
        totale_seed += len(batch)
        for voce in batch:
            chiave = (voce["giocatore"].lower(), voce["squadra"])
            if chiave in esistenti:
                continue
            nuova = dict(voce)
            nuova["aggiunto_il"] = raccolta_il
            stato["scommesse"].append(nuova)
            aggiunte.append(nuova["giocatore"])
            esistenti.add(chiave)
    if aggiunte:
        _salva(stato)
    return {"aggiunte": aggiunte, "gia_presenti": totale_seed - len(aggiunte),
            "totale_in_archivio": len(stato["scommesse"])}
