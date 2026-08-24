"""
Strumenti (tool) che Claude puo' chiamare via API per interrogare i nostri dati:
- classifica_reparto : usa la logica di scripts/ranking_reparto.py
- cerca_giocatori    : filtro libero sul dataset unificato
- dettaglio_giocatore: scheda completa di uno o piu' giocatori (per confronti)

Ogni tool ha: definizione JSON (schema) + funzione Python che lo esegue.
I dati vengono dal dataset gia' costruito (data/dataset_unificato.csv).
"""
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import ranking_reparto as rr  # noqa: E402  (usa DATASET, REPARTI, classifica, metriche)

DATASET = REPO / "data" / "dataset_unificato.csv"

# campi "sintetici" restituiti nelle ricerche (compatti, per non riempire il contesto)
CAMPI_SINTESI = [
    "nome", "squadra", "ruolo_mantra", "mantra_qa", "mantra_fvm",
    "continuita_pct", "fm_media_pesata", "trend_fm",
    "nessuno_storico", "cambio_squadra", "pos_media_squadra",
]


def _carica():
    with open(DATASET, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _ruoli_da_reparto(reparto_o_ruoli):
    """Accetta 'por/dif/cen/att' oppure una lista di ruoli Mantra."""
    if isinstance(reparto_o_ruoli, str) and reparto_o_ruoli in rr.REPARTI:
        return set(rr.REPARTI[reparto_o_ruoli]["ruoli"])
    if isinstance(reparto_o_ruoli, str):
        return {x.strip().lower() for x in reparto_o_ruoli.split(",") if x.strip()}
    return {str(x).strip().lower() for x in (reparto_o_ruoli or [])}


# ---------------------------------------------------------------- classifica
def classifica_reparto(reparto: str, top: int = 15) -> dict:
    rows = rr.carica()
    preset = reparto if reparto in rr.REPARTI else None
    ruoli = None if preset else [x.strip().lower() for x in reparto.split(",")]
    top_list, senza = rr.classifica(rows, reparto=preset, ruoli=ruoli, top=top)
    out = []
    for pos, (score, r, m) in enumerate(top_list, 1):
        out.append({
            "pos": pos, "nome": r["nome"], "squadra": r["squadra"],
            "ruolo_mantra": r["ruolo_mantra"], "quotazione_mantra": r["mantra_qa"],
            "score": round(score, 3),
            "continuita_pct": r["continuita_pct"],
            "fm_media_pesata": r["fm_media_pesata"], "trend": r["trend_fm"],
            "motivazione": rr.motivazione(r, m, preset),
        })
    return {"reparto": reparto, "classifica": out,
            "senza_storico": [
                {"nome": s["nome"], "squadra": s["squadra"],
                 "ruolo_mantra": s["ruolo_mantra"], "quotazione_mantra": s["mantra_qa"]}
                for s in sorted(senza, key=lambda x: -int(x["mantra_qa"] or 0))[:15]
            ]}


# ---------------------------------------------------------------- ricerca
def cerca_giocatori(ruoli=None, squadra=None, quotazione_max=None,
                    quotazione_min=None, solo_scommesse=False,
                    solo_con_storico=False, continuita_min=None,
                    trend=None, ordina_per="fvm", limite=20) -> dict:
    rows = _carica()
    target = _ruoli_da_reparto(ruoli) if ruoli else None
    res = []
    for r in rows:
        if target and not (set(r["ruolo_mantra"].split("/")) & target):
            continue
        if squadra and r["squadra"].strip().upper() != squadra.strip().upper():
            continue
        q = _num(r["mantra_qa"])
        if quotazione_max is not None and (q is None or q > quotazione_max):
            continue
        if quotazione_min is not None and (q is None or q < quotazione_min):
            continue
        if solo_scommesse and r["nessuno_storico"] != "1":
            continue
        if solo_con_storico and r["nessuno_storico"] == "1":
            continue
        if continuita_min is not None:
            c = _num(r["continuita_pct"])
            if c is None or c < continuita_min:
                continue
        if trend and r["trend_fm"] != trend:
            continue
        res.append({k: r[k] for k in CAMPI_SINTESI})

    chiavi = {"quotazione": "mantra_qa", "fvm": "mantra_fvm",
              "continuita": "continuita_pct", "fantamedia": "fm_media_pesata"}
    key = chiavi.get(ordina_per, "mantra_fvm")
    reverse = ordina_per != "quotazione_asc"
    res.sort(key=lambda x: (_num(x.get(key)) is None, -(_num(x.get(key)) or 0)))
    return {"totale_trovati": len(res), "giocatori": res[:limite]}


# ---------------------------------------------------------------- dettaglio
def dettaglio_giocatore(nome: str) -> dict:
    rows = _carica()
    q = nome.strip().lower()
    match = [r for r in rows if q in r["nome"].lower()]
    if not match:
        return {"trovati": 0, "giocatori": [],
                "messaggio": f"Nessun giocatore quotato contiene '{nome}'."}
    return {"trovati": len(match), "giocatori": match[:6]}


# ---------------------------------------------------------------- registro
FUNZIONI = {
    "classifica_reparto": classifica_reparto,
    "cerca_giocatori": cerca_giocatori,
    "dettaglio_giocatore": dettaglio_giocatore,
}

# schemi JSON esposti a Claude
TOOLS = [
    {
        "name": "classifica_reparto",
        "description": (
            "Classifica i migliori giocatori di un reparto secondo la strategia "
            "Mantra dell'utente (pesi dedicati per ruolo, malus cartellini, forza "
            "squadra per i portieri). Usa i preset 'por', 'dif', 'cen', 'att' "
            "oppure una lista di ruoli Mantra separati da virgola (es. 'dc,dd'). "
            "Restituisce anche i giocatori senza storico (possibili scommesse)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reparto": {"type": "string",
                            "description": "por | dif | cen | att, oppure ruoli tipo 'dc,dd'"},
                "top": {"type": "integer", "description": "quanti giocatori (default 15)"},
            },
            "required": ["reparto"],
        },
    },
    {
        "name": "cerca_giocatori",
        "description": (
            "Filtro libero sul dataset dei giocatori quotati. Utile per richieste "
            "tipo 'centrocampisti sotto i 10 crediti con continuita' alta' o "
            "'scommesse in attacco'. Combina piu' filtri."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ruoli": {"type": "string",
                          "description": "preset reparto (por/dif/cen/att) o ruoli 'm,c,t'"},
                "squadra": {"type": "string", "description": "sigla 3 lettere, es. INT"},
                "quotazione_max": {"type": "number"},
                "quotazione_min": {"type": "number"},
                "solo_scommesse": {"type": "boolean",
                                   "description": "solo giocatori senza storico in Serie A"},
                "solo_con_storico": {"type": "boolean"},
                "continuita_min": {"type": "number", "description": "percentuale minima 0-100"},
                "trend": {"type": "string", "enum": ["crescente", "stabile", "calante", "n_d"]},
                "ordina_per": {"type": "string",
                               "enum": ["fvm", "quotazione", "quotazione_asc",
                                        "continuita", "fantamedia"]},
                "limite": {"type": "integer", "description": "max risultati (default 20)"},
            },
        },
    },
    {
        "name": "dettaglio_giocatore",
        "description": (
            "Scheda completa di uno o piu' giocatori il cui nome contiene la stringa "
            "cercata: tutte le statistiche per stagione + colonne calcolate. "
            "Usalo per confronti tra due o piu' giocatori (chiamalo una volta per nome)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "nome": {"type": "string", "description": "anche parziale, es. 'Martinez'"},
            },
            "required": ["nome"],
        },
    },
]


def esegui(nome_tool: str, args: dict):
    """Esegue un tool per nome e restituisce il risultato (dict/list)."""
    fn = FUNZIONI.get(nome_tool)
    if fn is None:
        return {"errore": f"tool sconosciuto: {nome_tool}"}
    try:
        return fn(**(args or {}))
    except Exception as e:  # non far crashare il bot per un input strano
        return {"errore": f"{type(e).__name__}: {e}"}
