#!/usr/bin/env python3
"""
Estrattore infortunati/indisponibili Serie A da Fantacalcio.it.

Fonte: pagina PUBBLICA https://www.fantacalcio.it/infortunati-serie-a
Struttura: una "team-card" per squadra; dentro, una lista di <li> con
  <strong class="item-name">Nome</strong>
  <div class="item-description"><p>testo narrativo...</p></div>

Il testo del recupero e' NARRATIVO ("rientro a fine agosto", "da valutare"):
lo salviamo COSI' COM'E', senza forzarlo in una data. Salviamo anche la data di
estrazione (aggiornato_il): questa informazione cambia in fretta.

robots.txt di fantacalcio.it: /infortunati-serie-a NON e' bloccata.
Una sola richiesta per esecuzione, nessun retry aggressivo.

Uso:
    python3 scripts/estrai_infortuni.py                 # scarica e salva
    python3 scripts/estrai_infortuni.py --html f.html   # usa un HTML gia' salvato
Output: data/infortuni_seriea.csv
"""
import argparse
import csv
import datetime
import html as ihtml
import re
import sys
import urllib.request
from pathlib import Path

URL = "https://www.fantacalcio.it/infortunati-serie-a"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
OUT = Path(__file__).resolve().parent.parent / "data" / "infortuni_seriea.csv"

# nome squadra (come sul sito) -> sigla usata nel dataset
SQUADRA_CODICE = {
    "Atalanta": "ATA", "Bologna": "BOL", "Cagliari": "CAG", "Como": "COM",
    "Cremonese": "CRE", "Empoli": "EMP", "Fiorentina": "FIO", "Frosinone": "FRO",
    "Genoa": "GEN", "Hellas Verona": "VER", "Verona": "VER", "Inter": "INT",
    "Juventus": "JUV", "Lazio": "LAZ", "Lecce": "LEC", "Milan": "MIL",
    "Monza": "MON", "Napoli": "NAP", "Parma": "PAR", "Pisa": "PIS",
    "Roma": "ROM", "Salernitana": "SAL", "Sassuolo": "SAS", "Torino": "TOR",
    "Udinese": "UDI", "Venezia": "VEN",
}

HEADER = ["squadra", "squadra_nome", "nome", "stato_infortunio",
          "dettaglio_infortunio", "aggiornato_il"]


def scarica_html(url: str = URL) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def _pulisci(testo: str) -> str:
    """Rimuove tag HTML, decodifica entita', compatta gli spazi."""
    t = re.sub(r"<[^>]+>", " ", testo)
    t = ihtml.unescape(t).replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def parse(raw: str, oggi: str) -> list[list[str]]:
    out = []
    cards = re.split(r'class="card team-card"', raw)[1:]
    for c in cards:
        tm = re.search(r'class="team-name">([^<]+)</span>', c)
        squadra_nome = ihtml.unescape(tm.group(1).strip()) if tm else ""
        codice = SQUADRA_CODICE.get(squadra_nome, "")
        # ogni <li>: item-name + item-description
        for m in re.finditer(
                r'class="item-name">(.*?)</strong>.*?'
                r'class="item-description">(.*?)</div>', c, re.S):
            nome = _pulisci(m.group(1))
            dettaglio = _pulisci(m.group(2))
            if not nome:
                continue
            out.append([codice, squadra_nome, nome, "indisponibile", dettaglio, oggi])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Estrai infortunati Serie A")
    ap.add_argument("--html", help="HTML gia' scaricato (offline)")
    args = ap.parse_args()

    oggi = datetime.date.today().isoformat()
    raw = Path(args.html).read_text(encoding="utf-8", errors="replace") if args.html \
        else scarica_html()
    righe = parse(raw, oggi)
    if not righe:
        print("ATTENZIONE: nessun infortunato estratto (pagina cambiata?).",
              file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(righe)
    senza_codice = sum(1 for r in righe if not r[0])
    print(f"OK: {len(righe)} indisponibili salvati in {OUT} (aggiornato_il={oggi})")
    if senza_codice:
        print(f"  nota: {senza_codice} righe senza codice squadra (nome squadra non mappato)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
