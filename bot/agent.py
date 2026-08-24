"""
Agente Claude per il Fantacalcio Mantra.

- Carica CLAUDE.md come contesto di sistema (la strategia dell'utente).
- Espone i tool di bot/tools.py (dataset + logica di ranking).
- Esegue il loop manuale tool-use e restituisce la risposta testuale finale.

Nessuna chiave hardcoded: il client legge ANTHROPIC_API_KEY dall'ambiente.
Il modello e' configurabile con CLAUDE_MODEL (default: claude-opus-5).
"""
import json
import os
from pathlib import Path

import anthropic

from . import tools

REPO = Path(__file__).resolve().parent.parent
MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5")
MAX_TOKENS = 4000
MAX_GIRI_TOOL = 8  # limite di sicurezza sul loop tool-use

ISTRUZIONI_BOT = """\
Sei l'assistente personale di Fantacalcio (modalita' MANTRA) dell'utente.
Applica SEMPRE la strategia descritta qui sopra (reparti, filosofia, scommesse,
multiruolo, criteri di valutazione). Rispondi in italiano, in tono pratico e
sintetico, adatto a una chat Telegram: niente tabelle enormi, usa elenchi
puntati brevi e i dati che contano (quotazione Mantra, continuita', trend,
fantamedia/media voto, cambio squadra).

Hai a disposizione degli strumenti per interrogare i dati reali (dataset dei
giocatori quotati + logica di ranking per reparto). USA gli strumenti per
qualsiasi domanda su numeri, classifiche, confronti o filtri: non inventare
statistiche o quotazioni. Se un dato non c'e', dillo.

Quando confronti giocatori, chiama dettaglio_giocatore per ciascuno e motiva la
scelta secondo la strategia dell'utente. Segnala sempre i limiti onesti (poche
stagioni di storico, cambio squadra, rischio cartellini) quando emergono.

ASTA A RIALZO — la quotazione NON e' il prezzo pagato. L'asta parte da 1 credito
e si rilancia: quotazione Mantra e FVM sono solo un RIFERIMENTO di mercato, non
il prezzo reale. Distingui sempre due cose diverse:
- quanto vale il giocatore secondo i dati (quotazione/FVM come riferimento);
- quanto conviene pagarlo A TE (prezzo massimo personale, che puo' stare sopra
  o sotto la quotazione secondo la strategia).
Se l'utente indica un prezzo ("conviene arrivare a X?", "lo prendo a Y"), ragiona
sul rapporto qualita'/prezzo A QUEL PREZZO: un prezzo molto sotto quotazione e'
un affare da sfruttare, uno molto sopra va giustificato. Non limitarti a
ripetere la quotazione di listino.

TIMING D'ASTA — l'utente preferisce SEMPRE attendere che sia un altro ad aprire
il rilancio su un giocatore, e NON aprire mai per primo un'offerta su un nome
(nemmeno su una scommessa che desidera). Quando suggerisci una strategia per un
giocatore, formulala di conseguenza: "aspetta che qualcuno lo nomini, poi
rilancia fino a X" e non "nominalo/aprilo per primo". Se l'utente propone di
aprire lui per primo, faglielo notare gentilmente e proponi l'alternativa di
attendere. (Resta inteso che, quando nel giro d'asta tocca a lui chiamare un
giocatore rimasto, e' normale farlo: la preferenza riguarda il non essere il
primo a lanciare un'offerta aggressiva su un nome.)
"""


def _system_prompt() -> str:
    claude_md = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    return f"{claude_md}\n\n---\n\n{ISTRUZIONI_BOT}"


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def rispondi(domanda: str, storico=None, client=None) -> str:
    """Elabora una domanda dell'utente e restituisce la risposta testuale.

    `storico` (opzionale) e' la lista di messaggi precedenti (per multi-turno).
    """
    client = client or _client()
    messages = list(storico or [])
    messages.append({"role": "user", "content": domanda})

    for _ in range(MAX_GIRI_TOOL):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=_system_prompt(),
            tools=tools.TOOLS,
            messages=messages,
        )
        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            risultati = []
            for blocco in resp.content:
                if blocco.type == "tool_use":
                    esito = tools.esegui(blocco.name, blocco.input)
                    risultati.append({
                        "type": "tool_result",
                        "tool_use_id": blocco.id,
                        "content": json.dumps(esito, ensure_ascii=False),
                    })
            messages.append({"role": "user", "content": risultati})
            continue
        # risposta finale
        testo = "".join(b.text for b in resp.content if b.type == "text")
        return testo.strip() or "(nessuna risposta)"

    return "Mi sono fermato dopo troppi passaggi interni. Riprova a riformulare la domanda."
