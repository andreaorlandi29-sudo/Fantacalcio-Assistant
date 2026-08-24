#!/usr/bin/env python3
"""
Unisce quotazioni (2026/27) e statistiche storiche in un unico dataset.

Chiave di join: player_id (univoco su Fantacalcio.it, stabile tra stagioni e
indipendente da nome o cambio squadra).

Base = i giocatori QUOTATI per l'asta (data/quotazioni_fantacalcio.csv): sono
quelli che servono davvero. A ciascuno si affiancano, in colonne dedicate per
stagione, le statistiche storiche (data/statistiche_seriea.csv). Un giocatore
senza storico in Serie A (neopromosse, arrivi dall'estero, giovani) resta in
tabella con le colonne stat vuote: e' un'informazione utile (possibili
"scommesse").

Formato "largo": una riga per giocatore. Per ogni stagione le colonne:
    pg_<st>  mv_<st>  fm_<st>  gol_<st>  ass_<st>  amm_<st>  gs_<st>  rp_<st>

Uso:
    python3 scripts/unisci_dataset.py
Output:
    data/dataset_unificato.csv
"""
import csv
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
QUOT = DATA / "quotazioni_fantacalcio.csv"
STAT = DATA / "statistiche_seriea.csv"
OUT = DATA / "dataset_unificato.csv"

# statistica -> colonna nel file statistiche
STAT_FIELDS = {
    "pg": "pg", "mv": "mv", "fm": "fantamedia", "gol": "gol",
    "ass": "assist", "amm": "ammonizioni", "gs": "gol_subiti", "rp": "rig_parati",
}


def leggi(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    quot = leggi(QUOT)
    stat = leggi(STAT)

    # stagioni presenti, ordinate dalla piu' recente
    stagioni = sorted({r["stagione"] for r in stat}, reverse=True)
    # indice: (player_id, stagione) -> riga statistiche
    idx = {(r["player_id"], r["stagione"]): r for r in stat if r["player_id"]}

    def suf(st: str) -> str:
        return st.replace("-", "_")  # 2025-26 -> 2025_26

    base_cols = ["player_id", "nome", "squadra", "ruolo_mantra", "ruolo_classic",
                 "mantra_qa", "mantra_fvm", "classic_qa", "classic_fvm"]
    stat_cols = [f"{k}_{suf(st)}" for st in stagioni for k in STAT_FIELDS]
    header = base_cols + stat_cols

    righe = []
    for q in quot:
        row = {
            "player_id": q["player_id"], "nome": q["nome"], "squadra": q["squadra"],
            "ruolo_mantra": q["ruolo_mantra"], "ruolo_classic": q["ruolo_classic"],
            "mantra_qa": q["mantra_qa"], "mantra_fvm": q["mantra_fvm"],
            "classic_qa": q["classic_qa"], "classic_fvm": q["classic_fvm"],
        }
        for st in stagioni:
            s = idx.get((q["player_id"], st))
            for k, src in STAT_FIELDS.items():
                row[f"{k}_{suf(st)}"] = s[src] if s else ""
        righe.append(row)

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(righe)

    con_storico = sum(1 for q in righe if any(
        q[f"pg_{suf(st)}"] for st in stagioni))
    print(f"OK: {len(righe)} giocatori quotati -> {OUT}")
    print(f"  con almeno una stagione di storico: {con_storico}")
    print(f"  senza storico (rookie/estero/neopromosse): {len(righe) - con_storico}")
    print(f"  stagioni incluse: {', '.join(stagioni)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
