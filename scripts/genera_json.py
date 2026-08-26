#!/usr/bin/env python3
"""
Converte il dataset unificato (data/dataset_unificato.csv) in un JSON pulito,
pensato per essere PUBBLICO (pagina web + bot). Contiene SOLO dati dei
giocatori: nessun codice, nessuna strategia.

Struttura (oggetto con metadati + array 'giocatori'):
{
  "aggiornato_il": "2026-08-25",
  "totale": 540,
  "stagioni": ["2025-26","2024-25","2023-24"],
  "giocatori": [
    {
      "player_id": "5585",
      "nome": "Malen",
      "squadra": "ROM",
      "ruolo_mantra": "pc",
      "ruolo_classic": "a",
      "quotazioni": {"mantra": {"qa": 34, "fvm": 365},
                     "classic": {"qa": 34, "fvm": 365}},
      "indicatori": {"valutazione": 18, "fm_media_pesata": 8.97, "trend_fm": "n_d",
                     "continuita_pct": 47, "pos_media_squadra": 4.67,
                     "scommessa": false, "cambio_squadra": false},
      "stagioni": {"2025-26": {"pg":18,"mv":6.72,"fm":8.97,"gol":14,"assist":2,
                               "ammonizioni":1,"espulsioni":0,"gol_subiti":0,
                               "rigori_parati":0,"presenze_pct":47}, ...},
      "infortunio": {"stato":"indisponibile","dettaglio":"...","aggiornato_il":"..."} | null
    }, ...
  ]
}

Uso:  python3 scripts/genera_json.py [--out percorso.json]
Default output: build/dati.json
"""
import argparse
import csv
import datetime
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATASET = REPO / "data" / "dataset_unificato.csv"
sys.path.insert(0, str(REPO / "scripts"))
from genera_lista import valutazioni  # noqa: E402  (valutazione 1-20 per reparto)

# statistica -> chiave leggibile nel JSON
STAT_MAP = {"pg": "pg", "mv": "mv", "fm": "fm", "gol": "gol", "ass": "assist",
            "amm": "ammonizioni", "esp": "espulsioni", "gs": "gol_subiti",
            "rp": "rigori_parati"}


def _num(v):
    """'8.97'->8.97, '14'->14, ''->None."""
    if v is None or v.strip() == "":
        return None
    try:
        f = float(v)
        return int(f) if f.is_integer() else f
    except ValueError:
        return None


def _bool(v):
    return v == "1"


def _stagioni(header) -> list[str]:
    # rileva le stagioni dai campi pg_YYYY_YY, ordinate dalla piu' recente
    st = sorted({m.group(1) for c in header if (m := re.match(r"pg_(\d{4}_\d{2})$", c))},
                reverse=True)
    return [s.replace("_", "-") for s in st]


def costruisci(rows: list[dict], header: list[str]) -> dict:
    stagioni = _stagioni(header)
    val_map = valutazioni()   # {player_id: valutazione 1-20}
    giocatori = []
    for r in rows:
        st_out = {}
        for st in stagioni:
            suf = st.replace("-", "_")
            if r.get(f"pg_{suf}", "") == "":
                continue  # nessun dato per quella stagione
            st_out[st] = {STAT_MAP[k]: _num(r.get(f"{k}_{suf}", ""))
                          for k in STAT_MAP}
            st_out[st]["presenze_pct"] = _num(r.get(f"pres_pct_{suf}", ""))

        inf = None
        if r.get("stato_infortunio"):
            inf = {"stato": r["stato_infortunio"],
                   "dettaglio": r.get("dettaglio_infortunio", ""),
                   "aggiornato_il": r.get("infortunio_aggiornato_il", "")}

        giocatori.append({
            "player_id": r["player_id"],
            "nome": r["nome"],
            "squadra": r["squadra"],
            "ruolo_mantra": r["ruolo_mantra"],
            "ruolo_classic": r["ruolo_classic"],
            "quotazioni": {
                "mantra": {"qa": _num(r["mantra_qa"]), "fvm": _num(r["mantra_fvm"])},
                "classic": {"qa": _num(r["classic_qa"]), "fvm": _num(r["classic_fvm"])},
            },
            "indicatori": {
                "valutazione": val_map.get(r["player_id"]),
                "fm_media_pesata": _num(r["fm_media_pesata"]),
                "trend_fm": r["trend_fm"] or None,
                "continuita_pct": _num(r["continuita_pct"]),
                "pos_media_squadra": _num(r["pos_media_squadra"]),
                "scommessa": _bool(r["nessuno_storico"]),
                "cambio_squadra": _bool(r["cambio_squadra"]),
            },
            "stagioni": st_out,
            "infortunio": inf,
        })

    return {"aggiornato_il": datetime.date.today().isoformat(),
            "totale": len(giocatori), "stagioni": stagioni,
            "giocatori": giocatori}


def main():
    ap = argparse.ArgumentParser(description="Converte il dataset in JSON pubblico")
    ap.add_argument("--out", default=str(REPO / "build" / "dati.json"))
    args = ap.parse_args()
    with open(DATASET, encoding="utf-8") as f:
        rd = csv.DictReader(f)
        rows = list(rd)
        header = rd.fieldnames
    doc = costruisci(rows, header)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    print(f"OK: {doc['totale']} giocatori -> {out} ({out.stat().st_size} byte)")


if __name__ == "__main__":
    main()
