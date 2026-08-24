"""
Banco di prova LOCALE dell'agente, senza Telegram.

Serve a verificare che i tool e la strategia funzionino, usando solo la
ANTHROPIC_API_KEY (nessun token Telegram necessario).

Uso:
  python3 -m bot.dry_run "i migliori 10 difensori"
  python3 -m bot.dry_run            # modalita' interattiva (invio vuoto per uscire)
"""
import os
import sys

from . import agent


def _una(domanda: str):
    print(f"\n>>> {domanda}\n")
    print(agent.rispondi(domanda))


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ERRORE: manca ANTHROPIC_API_KEY nell'ambiente.")
    if len(sys.argv) > 1:
        _una(" ".join(sys.argv[1:]))
        return
    print("Modalita' interattiva (invio vuoto per uscire).")
    while True:
        try:
            d = input("\nDomanda> ").strip()
        except EOFError:
            break
        if not d:
            break
        _una(d)


if __name__ == "__main__":
    main()
