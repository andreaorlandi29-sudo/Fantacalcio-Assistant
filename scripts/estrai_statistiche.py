#!/usr/bin/env python3
"""
Estrattore statistiche giocatori Serie A da Fantacalcio.it (multi-stagione).

Fonte: pagina PUBBLICA https://www.fantacalcio.it/statistiche-serie-a/<STAGIONE>
La tabella e' server-side nell'HTML (nessun login richiesto). La stagione si
seleziona nel PERCORSO dell'URL, formato AAAA-AA (es. 2025-26).

robots.txt di fantacalcio.it (verificato): /statistiche-serie-a NON e' bloccata.
Per correttezza si aspetta qualche secondo tra una stagione e l'altra.

Colonne statistiche (data-col-key nella pagina):
  pg  = partite a voto        mv  = media voto        mfv = fantamedia
  gol = gol fatti             gs  = gol subiti (portieri)
  rig = "segnati / tirati"    rp  = rigori parati (portieri)
  ass = assist                amm = ammonizioni       esp = espulsioni

Uso:
    python3 scripts/estrai_statistiche.py                       # 3 stagioni default
    python3 scripts/estrai_statistiche.py 2025-26 2024-25       # stagioni scelte

Output (formato "lungo": una riga per giocatore per stagione):
    data/statistiche_seriea.csv
"""
import csv
import html as ihtml
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://www.fantacalcio.it/statistiche-serie-a"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
OUT = Path(__file__).resolve().parent.parent / "data" / "statistiche_seriea.csv"
STAGIONI_DEFAULT = ["2025-26", "2024-25", "2023-24"]
PAUSA_SEC = 3  # cortesia tra una richiesta e l'altra

HEADER = ["player_id", "nome", "squadra", "stagione",
          "pg", "mv", "fantamedia", "gol", "gol_subiti",
          "rig_segnati", "rig_tirati", "rig_parati", "assist",
          "ammonizioni", "espulsioni"]


def scarica_html(stagione: str) -> str:
    url = f"{BASE}/{stagione}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def _col(block: str, key: str) -> str:
    m = re.search(r'data-col-key="' + key + r'"[^>]*>\s*(.*?)\s*</td>', block, re.S)
    return m.group(1).strip() if m else ""


def _num(s: str) -> str:
    """Normalizza i decimali italiani (7,5 -> 7.5). '--' o vuoto -> ''."""
    s = s.strip()
    if s in ("", "--"):
        return ""
    return s.replace(",", ".")


def parse(raw: str, stagione: str) -> list[list[str]]:
    righe = re.split(r'<tr class="player-row"', raw)[1:]
    out = []
    for b in righe:
        nome_m = re.search(
            r'class="player-name player-link".*?<span>(.*?)</span>', b, re.S)
        nome = ihtml.unescape(nome_m.group(1).strip()) if nome_m else ""
        if not nome:
            continue
        id_m = re.search(r'/serie-a/squadre/[^"/]+/[^"/]+/(\d+)', b)
        player_id = id_m.group(1) if id_m else ""
        team_m = re.search(r'class="player-team"[^>]*>\s*(.*?)\s*</td>', b, re.S)
        squadra = team_m.group(1).strip() if team_m else ""
        # rigori: formato "segnati / tirati"
        rig = _col(b, "rig")
        if "/" in rig:
            rig_seg, rig_tir = (p.strip() for p in rig.split("/", 1))
        else:
            rig_seg, rig_tir = rig.strip(), ""
        out.append([
            player_id, nome, squadra, stagione,
            _num(_col(b, "pg")), _num(_col(b, "mv")), _num(_col(b, "mfv")),
            _num(_col(b, "gol")), _num(_col(b, "gs")),
            _num(rig_seg), _num(rig_tir), _num(_col(b, "rp")),
            _num(_col(b, "ass")), _num(_col(b, "amm")), _num(_col(b, "esp")),
        ])
    return out


def main() -> int:
    stagioni = sys.argv[1:] or STAGIONI_DEFAULT
    tutte = []
    for i, st in enumerate(stagioni):
        if i:
            time.sleep(PAUSA_SEC)
        print(f"Scarico stagione {st} ...", flush=True)
        righe = parse(scarica_html(st), st)
        print(f"  -> {len(righe)} giocatori")
        tutte.extend(righe)
    if not tutte:
        print("ERRORE: nessun dato estratto.", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(tutte)
    print(f"OK: {len(tutte)} righe (giocatore x stagione) salvate in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
