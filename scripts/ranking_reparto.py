#!/usr/bin/env python3
"""
Ranking giocatori per REPARTO secondo la strategia del CLAUDE.md.

Legge data/dataset_unificato.csv e produce una classifica per un reparto Mantra
(o per una lista di ruoli scelta a mano), con punteggio, quotazione e una
motivazione generata dai dati.

Filosofia per reparto (dal CLAUDE.md), tradotta in pesi di punteggio:
  portieri (por)     -> titolarita' + affidabilita'   : continuita' + fantamedia
  difensori (dif)    -> continuita', NIENTE bonus      : continuita' >> fantamedia, malus cartellini pesante
  centrocampisti (cen) -> potenziale bonus gol/assist  : bonus (gol+assist) al centro del punteggio
  attaccanti (att)   -> pilastri forti + comprimari    : bonus e fantamedia dominano; ranking evidenzia pilastri

Regole comuni a TUTTI i reparti (richieste esplicitamente):
  - Le ESPULSIONI pesano come malus piu' delle ammonizioni (fattore ESP_SU_AMM).
  - Se cambio_squadra = 1, la motivazione riporta una nota di cautela: lo storico
    potrebbe non riflettere il rendimento 2026/27.

Note di metodo:
  - I giocatori senza storico in Serie A non sono classificabili sul rendimento:
    vengono elencati a parte come "scommesse / da valutare" ordinati per quotazione.
  - Le metriche continuita'/fantamedia/bonus/cartellini sono normalizzate min-max
    DENTRO il pool del reparto, quindi il punteggio e' relativo al reparto stesso.
  - I pesi sono dichiarati in REPARTI e sono facilmente modificabili.

Uso:
    python3 scripts/ranking_reparto.py dif                 # preset reparto
    python3 scripts/ranking_reparto.py att --top 20
    python3 scripts/ranking_reparto.py --roles dc,dd       # ruoli a mano
    python3 scripts/ranking_reparto.py cen --csv out.csv   # salva anche in CSV
"""
import argparse
import csv
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
DATASET = DATA / "dataset_unificato.csv"
STAGIONI = ["2025_26", "2024_25", "2023_24"]     # dalla piu' recente
PESI_ST = [0.5, 0.3, 0.2]                          # ultima/penultima/terzultima
SOGLIA_PG = 5                                      # min presenze perche' una stagione conti
ESP_SU_AMM = 3.0                                   # 1 espulsione pesa come 3 ammonizioni

# preset di reparto: ruoli Mantra, pesi e metrica di "qualita'".
#   w = (continuita, qualita, bonus_gol_assist, malus_cartellini, forza_squadra)
#   qualita = "mv" (media voto, RENDIMENTO PURO senza bonus) per por/dif,
#             perche' sui difensori NON si cercano bonus offensivi;
#           = "fm" (fantamedia, bonus inclusi) per cen/att, dove i bonus contano.
#   forza_squadra pesa SOLO per i portieri: premia i portieri di squadre
#   stabilmente in alta classifica (criterio "titolare di squadra medio-alta").
REPARTI = {
    "por": {"ruoli": ["por"],              "qualita": "mv", "w": (0.35, 0.30, 0.00, 0.10, 0.25)},
    "dif": {"ruoli": ["dc", "dd", "ds"],   "qualita": "mv", "w": (0.62, 0.20, 0.00, 0.25, 0.00)},
    "cen": {"ruoli": ["e", "m", "c", "t"], "qualita": "fm", "w": (0.30, 0.25, 0.45, 0.10, 0.00)},
    "att": {"ruoli": ["w", "a", "pc"],     "qualita": "fm", "w": (0.25, 0.30, 0.45, 0.05, 0.00)},
}
NOMI_REPARTO = {"por": "PORTIERI", "dif": "DIFENSORI",
                "cen": "CENTROCAMPISTI", "att": "ATTACCANTI"}


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _pesata(valori_per_stagione):
    """Media pesata (50/30/20) sulle stagioni valide; None se nessuna."""
    num = den = 0.0
    for i, v in enumerate(valori_per_stagione):
        if v is None:
            continue
        w = PESI_ST[i] if i < len(PESI_ST) else PESI_ST[-1]
        num += w * v
        den += w
    return (num / den) if den else None


def carica():
    with open(DATASET, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def metriche(r):
    """Estrae le metriche grezze usate per il punteggio da una riga dataset."""
    # stagioni valide = pg >= soglia (per mv/fm e bonus)
    mv_valide, fm_valide, gol_valide, ass_valide = [], [], [], []
    for st in STAGIONI:
        pg = _f(r[f"pg_{st}"])
        valida = pg is not None and pg >= SOGLIA_PG
        mv_valide.append(_f(r[f"mv_{st}"]) if valida else None)
        fm_valide.append(_f(r[f"fm_{st}"]) if valida else None)
        gol_valide.append(_f(r[f"gol_{st}"]) if valida else None)
        ass_valide.append(_f(r[f"ass_{st}"]) if valida else None)

    # cartellini: medie per stagione con dati (su tutte le stagioni giocate)
    amm, esp, n = 0.0, 0.0, 0
    for st in STAGIONI:
        if r[f"pg_{st}"] not in ("", None):
            amm += _f(r[f"amm_{st}"]) or 0
            esp += _f(r[f"esp_{st}"]) or 0
            n += 1
    amm_avg = (amm / n) if n else 0.0
    esp_avg = (esp / n) if n else 0.0
    card_malus = amm_avg + ESP_SU_AMM * esp_avg   # espulsioni pesate ESP_SU_AMM volte

    g, a = _pesata(gol_valide), _pesata(ass_valide)
    bonus = ((g or 0) + (a or 0)) if (g is not None or a is not None) else None
    # forza squadra: posizione media Serie A (piu' bassa = squadra piu' forte)
    pos = _f(r.get("pos_media_squadra"))
    return {"cont": _f(r["continuita_pct"]),
            "mv": _pesata(mv_valide), "fm": _pesata(fm_valide),
            "bonus": bonus, "card": card_malus,
            "amm_avg": amm_avg, "esp_avg": esp_avg,
            "pos_squadra": pos, "forza": (-pos if pos is not None else None),
            "n_stagioni": n}


def _norm(valori):
    """min-max su lista con eventuali None -> dict indice->0..1 (None -> 0)."""
    presenti = [v for v in valori if v is not None]
    if not presenti:
        return [0.0] * len(valori)
    lo, hi = min(presenti), max(presenti)
    rng = (hi - lo) or 1.0
    return [((v - lo) / rng) if v is not None else 0.0 for v in valori]


def motivazione(r, m, reparto):
    usa_mv = reparto in ("por", "dif")
    cont = f"{m['cont']:.0f}%" if m["cont"] is not None else "n/d"
    q = m["mv"] if usa_mv else m["fm"]
    q_txt = f"{q:.2f}" if q is not None else "n/d"
    q_lbl = "media voto" if usa_mv else "fantamedia"
    parti = [f"continuita' {cont}", f"{q_lbl} {q_txt}", f"trend {r['trend_fm']}"]
    if reparto in ("cen", "att") and m["bonus"] is not None:
        parti.append(f"bonus g+a ~{m['bonus']:.1f}/stag")
    # forza squadra: solo per i portieri
    if reparto == "por" and m["pos_squadra"] is not None:
        p = m["pos_squadra"]
        fascia = "alta" if p <= 8 else "media" if p <= 13 else "bassa"
        parti.append(f"forza squadra: pos. media {p:.1f} (classifica {fascia})")
    # nota cartellini solo se davvero rilevante
    if m["amm_avg"] >= 5 or m["esp_avg"] > 0:
        nota = f"cartellini: ~{m['amm_avg']:.1f} amm/stag"
        if m["esp_avg"] > 0:
            nota += f" + {m['esp_avg']:.1f} esp/stag"
        parti.append(nota)
    testo = ", ".join(parti)
    # NOTA (non penalita') se lo storico copre meno di 3 stagioni
    if m["n_stagioni"] == 1:
        testo += "  [nota: dato su 1 sola stagione, da considerare con cautela]"
    elif m["n_stagioni"] == 2:
        testo += "  [nota: dato su 2 stagioni]"
    if r["cambio_squadra"] == "1":
        testo += "  [!] cambio squadra 2026/27: lo storico potrebbe non riflettere il rendimento"
    return testo


def classifica(rows, reparto=None, ruoli=None, top=15):
    ruoli_target = set(ruoli) if ruoli else set(REPARTI[reparto]["ruoli"])
    w_cont, w_fm, w_bonus, w_card, w_forza = (REPARTI[reparto]["w"] if reparto
                                              else (0.4, 0.3, 0.3, 0.15, 0.0))

    def is_target(r):
        return bool(set(r["ruolo_mantra"].split("/")) & ruoli_target)

    pool = [r for r in rows if is_target(r)]
    con_storico = [r for r in pool if r["nessuno_storico"] != "1"]
    senza_storico = [r for r in pool if r["nessuno_storico"] == "1"]

    qfield = REPARTI[reparto]["qualita"] if reparto else "fm"
    met = [metriche(r) for r in con_storico]
    n_cont = _norm([m["cont"] for m in met])
    n_qual = _norm([m[qfield] for m in met])   # mv per por/dif, fm per cen/att
    n_bonus = _norm([m["bonus"] for m in met])
    n_card = _norm([m["card"] for m in met])
    n_forza = _norm([m["forza"] for m in met])  # piu' alto = squadra piu' forte

    scored = []
    for r, m, c, f, b, cm, fz in zip(con_storico, met, n_cont, n_qual,
                                     n_bonus, n_card, n_forza):
        score = (w_cont * c + w_fm * f + w_bonus * b
                 - w_card * cm + w_forza * fz)
        score += {"crescente": 0.03, "calante": -0.03}.get(r["trend_fm"], 0.0)
        scored.append((score, r, m))
    scored.sort(key=lambda x: -x[0])
    return scored[:top], senza_storico


def main():
    ap = argparse.ArgumentParser(description="Ranking per reparto (strategia CLAUDE.md)")
    ap.add_argument("reparto", nargs="?", choices=list(REPARTI),
                    help="por | dif | cen | att")
    ap.add_argument("--roles", help="lista ruoli Mantra separati da virgola (alternativa al reparto)")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--csv", help="salva la classifica anche in questo file CSV")
    args = ap.parse_args()

    if not args.reparto and not args.roles:
        ap.error("specifica un reparto (por/dif/cen/att) oppure --roles")

    rows = carica()
    ruoli = [x.strip().lower() for x in args.roles.split(",")] if args.roles else None
    top, senza = classifica(rows, reparto=args.reparto, ruoli=ruoli, top=args.top)

    titolo = NOMI_REPARTO.get(args.reparto, f"RUOLI {args.roles}")
    print(f"\n=== CLASSIFICA {titolo} (top {args.top}) ===\n")
    print(f"{'#':>2} {'GIOCATORE':<16}{'SQ':<4}{'RUOLO':<8}{'Q':>3}{'SCORE':>7}  MOTIVAZIONE")
    print("-" * 110)
    for i, (score, r, m) in enumerate(top, 1):
        print(f"{i:>2} {r['nome']:<16}{r['squadra']:<4}{r['ruolo_mantra']:<8}"
              f"{r['mantra_qa']:>3}{score:>7.3f}  {motivazione(r, m, args.reparto)}")

    if senza:
        senza.sort(key=lambda r: -int(r["mantra_qa"] or 0))
        print(f"\n--- Senza storico Serie A ({len(senza)}) - scommesse / da valutare a parte ---")
        for r in senza[:12]:
            nota = "  [!] cambio squadra" if r["cambio_squadra"] == "1" else ""
            print(f"   {r['nome']:<16}{r['squadra']:<4}{r['ruolo_mantra']:<8}Q={r['mantra_qa']}{nota}")

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["pos", "nome", "squadra", "ruolo_mantra", "quotazione",
                        "score", "continuita_pct", "fm_pesata", "bonus_ga",
                        "card_malus", "trend", "cambio_squadra", "motivazione"])
            for i, (score, r, m) in enumerate(top, 1):
                w.writerow([i, r["nome"], r["squadra"], r["ruolo_mantra"],
                            r["mantra_qa"], round(score, 3),
                            m["cont"], None if m["fm"] is None else round(m["fm"], 2),
                            None if m["bonus"] is None else round(m["bonus"], 2),
                            round(m["card"], 2), r["trend_fm"], r["cambio_squadra"],
                            motivazione(r, m, args.reparto)])
        print(f"\nSalvato CSV: {args.csv}")


if __name__ == "__main__":
    raise SystemExit(main())
