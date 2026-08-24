#!/usr/bin/env python3
"""
Unisce quotazioni (2026/27) e statistiche storiche in un unico dataset,
aggiungendo colonne calcolate utili alla valutazione.

Chiave di join: player_id (univoco su Fantacalcio.it, stabile tra stagioni e
indipendente da nome o cambio squadra).

Base = i giocatori QUOTATI per l'asta (data/quotazioni_fantacalcio.csv). A
ciascuno si affiancano, in colonne dedicate per stagione, le statistiche
storiche (data/statistiche_seriea.csv), piu' le colonne calcolate qui sotto.

Colonne calcolate:
  nessuno_storico     1 se il giocatore non ha alcuna presenza nelle stagioni
                      considerate (rookie / arrivi dall'estero / neopromosse) -> filtrabile come "scommessa"
  cambio_squadra      1 se la squadra 2026/27 (quotazioni) e' diversa da quella
                      dell'ultima stagione con dati; "" se nessuno storico
  fm_media_pesata     media della fantamedia sulle stagioni VALIDE, con pesi
                      50% ultima / 30% penultima / 20% terzultima (rinormalizzati
                      sulle stagioni effettivamente presenti)
  trend_fm            crescente / stabile / calante / n_d  (confronto fantamedia
                      tra prima e ultima stagione valida; soglia +/-0.3)
  pres_pct_<st>       % presenze nella stagione (partite a voto / 38)
  continuita_pct      media delle % presenze sulle stagioni con dati

NB: una stagione e' "valida" per media pesata e trend solo se il giocatore ha
almeno SOGLIA_PG_VALIDA presenze: cosi' una fantamedia gonfiata da 1-2 partite
non falsa il giudizio. Le presenze % invece si calcolano su tutte le stagioni.

Uso:  python3 scripts/unisci_dataset.py
Output:  data/dataset_unificato.csv
"""
import csv
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
QUOT = DATA / "quotazioni_fantacalcio.csv"
STAT = DATA / "statistiche_seriea.csv"
CLASS = DATA / "classifiche_squadre.csv"   # posizioni finali Serie A ultime 3 stagioni
OUT = DATA / "dataset_unificato.csv"

PARTITE_STAGIONE = 38          # Serie A a 20 squadre
SOGLIA_PG_VALIDA = 5           # min presenze perche' una stagione conti per fm/trend
PESI = [0.5, 0.3, 0.2]         # ultima, penultima, terzultima stagione

# statistica -> colonna nel file statistiche
STAT_FIELDS = {
    "pg": "pg", "mv": "mv", "fm": "fantamedia", "gol": "gol",
    "ass": "assist", "amm": "ammonizioni", "esp": "espulsioni",
    "gs": "gol_subiti", "rp": "rig_parati",
}


def leggi(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _f(v: str):
    """Converte in float, o None se vuoto/non valido."""
    if v is None or v.strip() == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def main() -> int:
    quot = leggi(QUOT)
    stat = leggi(STAT)

    # forza squadra: posizione media Serie A ultime 3 stagioni (20 = non in A)
    pos_media = {}
    for c in leggi(CLASS):
        p = [_f(c["pos_2023_24"]), _f(c["pos_2024_25"]), _f(c["pos_2025_26"])]
        p = [x for x in p if x is not None]
        if p:
            pos_media[c["squadra"].strip().upper()] = round(sum(p) / len(p), 2)

    # stagioni presenti, dalla piu' recente alla piu' vecchia
    stagioni = sorted({r["stagione"] for r in stat}, reverse=True)
    idx = {(r["player_id"], r["stagione"]): r for r in stat if r["player_id"]}

    def suf(st: str) -> str:
        return st.replace("-", "_")  # 2025-26 -> 2025_26

    base_cols = ["player_id", "nome", "squadra", "ruolo_mantra", "ruolo_classic",
                 "mantra_qa", "mantra_fvm", "classic_qa", "classic_fvm"]
    stat_cols = [f"{k}_{suf(st)}" for st in stagioni for k in STAT_FIELDS]
    calc_cols = (["nessuno_storico", "cambio_squadra", "fm_media_pesata", "trend_fm"]
                 + [f"pres_pct_{suf(st)}" for st in stagioni]
                 + ["continuita_pct", "pos_media_squadra"])
    header = base_cols + stat_cols + calc_cols

    righe = []
    for q in quot:
        row = {
            "player_id": q["player_id"], "nome": q["nome"], "squadra": q["squadra"],
            "ruolo_mantra": q["ruolo_mantra"], "ruolo_classic": q["ruolo_classic"],
            "mantra_qa": q["mantra_qa"], "mantra_fvm": q["mantra_fvm"],
            "classic_qa": q["classic_qa"], "classic_fvm": q["classic_fvm"],
        }
        # statistiche grezze per stagione
        stagioni_dati = {}  # st -> riga stat
        for st in stagioni:
            s = idx.get((q["player_id"], st))
            if s:
                stagioni_dati[st] = s
            for k, src in STAT_FIELDS.items():
                row[f"{k}_{suf(st)}"] = s[src] if s else ""

        # --- colonne calcolate ---
        row["nessuno_storico"] = 0 if stagioni_dati else 1

        # cambio squadra: confronto con l'ultima stagione (piu' recente) con dati
        if stagioni_dati:
            ultima = next(st for st in stagioni if st in stagioni_dati)
            sq_prec = stagioni_dati[ultima]["squadra"].strip().upper()
            row["cambio_squadra"] = 1 if q["squadra"].strip().upper() != sq_prec else 0
        else:
            row["cambio_squadra"] = ""

        # presenze % per stagione + continuita media
        pres_list = []
        for st in stagioni:
            s = stagioni_dati.get(st)
            pg = _f(s["pg"]) if s else None
            if pg is not None:
                pct = round(100 * pg / PARTITE_STAGIONE)
                row[f"pres_pct_{suf(st)}"] = pct
                pres_list.append(pct)
            else:
                row[f"pres_pct_{suf(st)}"] = ""
        row["continuita_pct"] = round(sum(pres_list) / len(pres_list)) if pres_list else ""

        # forza squadra 2026/27 (posizione media Serie A ultime 3 stagioni)
        row["pos_media_squadra"] = pos_media.get(q["squadra"].strip().upper(), "")

        # stagioni VALIDE (pg >= soglia) con fantamedia, dalla piu' recente
        valide = []  # (indice_stagione, fm)
        for i, st in enumerate(stagioni):
            s = stagioni_dati.get(st)
            if not s:
                continue
            pg, fm = _f(s["pg"]), _f(s["fantamedia"])
            if pg is not None and pg >= SOGLIA_PG_VALIDA and fm is not None:
                valide.append((i, fm))

        # media pesata (pesi rinormalizzati sulle valide)
        if valide:
            num = den = 0.0
            for i, fm in valide:
                w = PESI[i] if i < len(PESI) else PESI[-1]
                num += w * fm
                den += w
            row["fm_media_pesata"] = round(num / den, 2)
        else:
            row["fm_media_pesata"] = ""

        # trend: confronto fantamedia prima vs ultima stagione valida
        if len(valide) >= 2:
            fm_recente = valide[0][1]           # stagione piu' recente valida
            fm_vecchia = valide[-1][1]          # stagione piu' vecchia valida
            delta = fm_recente - fm_vecchia
            row["trend_fm"] = ("crescente" if delta >= 0.3
                               else "calante" if delta <= -0.3 else "stabile")
        else:
            row["trend_fm"] = "n_d"

        righe.append(row)

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(righe)

    con_storico = sum(1 for r in righe if not r["nessuno_storico"])
    cambi = sum(1 for r in righe if r["cambio_squadra"] == 1)
    print(f"OK: {len(righe)} giocatori quotati -> {OUT}")
    print(f"  con storico Serie A: {con_storico}  |  senza storico (scommesse): {len(righe)-con_storico}")
    print(f"  con cambio squadra 2026/27: {cambi}")
    print(f"  stagioni incluse: {', '.join(stagioni)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
