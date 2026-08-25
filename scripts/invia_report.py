#!/usr/bin/env python3
"""
Genera la lista giocatori in Excel e la invia via email come allegato.

Invio via SMTP Gmail con una App Password (semplice, nessun servizio terzo).
Credenziali da variabili d'ambiente (su GitHub: secret del repository):
  GMAIL_ADDRESS        indirizzo Gmail mittente (es. tuo@gmail.com)
  GMAIL_APP_PASSWORD   App Password generata nelle impostazioni Google
  EMAIL_TO             destinatario (se assente, usa GMAIL_ADDRESS)

Uso:
    python3 scripts/invia_report.py            # genera e invia
    python3 scripts/invia_report.py --dry-run  # genera ma NON invia (test)
"""
import argparse
import datetime
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path

from genera_lista import genera  # stesso folder scripts/ (aggiunto al path sotto)


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    ap = argparse.ArgumentParser(description="Invia la lista giocatori via email")
    ap.add_argument("--dry-run", action="store_true",
                    help="genera il file ma non invia (per i test)")
    args = ap.parse_args()

    oggi = datetime.date.today().isoformat()
    path = genera(data=oggi)
    print(f"File generato: {path} ({path.stat().st_size} byte)")

    mittente = os.environ.get("GMAIL_ADDRESS")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    destinatario = os.environ.get("EMAIL_TO") or mittente

    msg = EmailMessage()
    msg["Subject"] = f"Lista giocatori Fantacalcio - {oggi}"
    msg["From"] = mittente or "fantacalcio-bot"
    msg["To"] = destinatario or "(non impostato)"
    msg.set_content(
        "Ciao!\n\nIn allegato la lista aggiornata dei giocatori "
        f"({oggi}): valutazione 1-20 per reparto, situazione infortuni, "
        "filtri gia' attivi.\n\n"
        "Nota: le valutazioni delle scommesse (prefisso 🎲) sono stime prudenti; "
        "gli infortuni (⚠️) sono aggiornati alla data indicata nella cella e "
        "vanno riverificati a ridosso dell'asta.\n\n"
        "— Assistente Fantacalcio")
    with open(path, "rb") as f:
        msg.add_attachment(
            f.read(), maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=path.name)

    if args.dry_run:
        print(f"[DRY-RUN] Email NON inviata. To={msg['To']} | allegato={path.name}")
        return 0

    if not (mittente and password):
        print("ERRORE: mancano GMAIL_ADDRESS e/o GMAIL_APP_PASSWORD.", file=sys.stderr)
        return 1

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as smtp:
        smtp.login(mittente, password)
        smtp.send_message(msg)
    print(f"Email inviata a {destinatario} con allegato {path.name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
