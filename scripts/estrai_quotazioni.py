#!/usr/bin/env python3
"""
Estrattore quotazioni Fantacalcio (Classic + Mantra) da Fantacalcio.it.

Fonte: pagina PUBBLICA https://www.fantacalcio.it/quotazioni-fantacalcio
La tabella completa dei giocatori e' gia' presente nell'HTML server-side,
quindi non serve login (il pulsante "Scarica Excel" invece e' riservato ai
loggati e risponde 401: quello NON viene usato).

robots.txt di fantacalcio.it (verificato): blocca /ricerca,
/probabiliformazioniseriea, le preview e le cartelle di test. La pagina
/quotazioni-fantacalcio NON e' bloccata.

Uso:
    python3 scripts/estrai_quotazioni.py                 # scarica e salva CSV
    python3 scripts/estrai_quotazioni.py --html file.html  # usa un HTML gia' salvato

Output: data/quotazioni_fantacalcio.csv
"""
import argparse
import csv
import html as ihtml
import re
import sys
import urllib.request
from pathlib import Path

URL = "https://www.fantacalcio.it/quotazioni-fantacalcio"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
OUT = Path(__file__).resolve().parent.parent / "data" / "quotazioni_fantacalcio.csv"

HEADER = ["player_id", "nome", "squadra", "ruolo_classic", "ruolo_mantra",
          "classic_qi", "classic_qa", "classic_fvm",
          "mantra_qi", "mantra_qa", "mantra_fvm"]


def scarica_html(url: str = URL) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def _col(block: str, key: str) -> str:
    m = re.search(r'data-col-key="' + key + r'"[^>]*>\s*(.*?)\s*</td>', block, re.S)
    return m.group(1).strip() if m else ""


def parse(raw: str) -> list[list[str]]:
    """Estrae una riga per giocatore dai blocchi <tr class="player-row">."""
    righe = re.split(r'<tr class="player-row"', raw)[1:]
    out = []
    for b in righe:
        nome_m = re.search(
            r'class="player-name player-link".*?<span>(.*?)</span>', b, re.S)
        nome = ihtml.unescape(nome_m.group(1).strip()) if nome_m else ""
        if not nome:
            continue
        # ID univoco giocatore dall'href: .../squadre/<team>/<slug>/<ID>
        id_m = re.search(r'/serie-a/squadre/[^"/]+/[^"/]+/(\d+)', b)
        player_id = id_m.group(1) if id_m else ""
        team_m = re.search(r'class="player-team"[^>]*>\s*(.*?)\s*</td>', b, re.S)
        squadra = team_m.group(1).strip() if team_m else ""
        rc_m = re.search(r'player-role-classic.*?data-value="([^"]*)"', b, re.S)
        ruolo_classic = rc_m.group(1) if rc_m else ""
        # Mantra: puo' essere multiruolo -> piu' <span role role-mantra ...>
        m_block = re.search(r'player-role-mantra(.*?)</th>', b, re.S)
        ruoli_m = re.findall(
            r'role role-mantra" data-value="([^"]*)"', m_block.group(1)) if m_block else []
        ruolo_mantra = "/".join(ruoli_m)
        out.append([player_id, nome, squadra, ruolo_classic, ruolo_mantra,
                    _col(b, "c_qi"), _col(b, "c_qa"), _col(b, "c_fvm"),
                    _col(b, "m_qi"), _col(b, "m_qa"), _col(b, "m_fvm")])
    return out


def salva_csv(righe: list[list[str]], out: Path = OUT) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(righe)


def main() -> int:
    ap = argparse.ArgumentParser(description="Estrai quotazioni Fantacalcio Mantra/Classic")
    ap.add_argument("--html", help="Percorso a un HTML gia' scaricato (offline)")
    args = ap.parse_args()

    raw = Path(args.html).read_text(encoding="utf-8", errors="replace") if args.html \
        else scarica_html()
    righe = parse(raw)
    if not righe:
        print("ERRORE: nessun giocatore estratto (la pagina puo' essere cambiata).",
              file=sys.stderr)
        return 1
    salva_csv(righe)
    print(f"OK: {len(righe)} giocatori salvati in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
