# Assistente Fantacalcio Mantra

Assistente personale per il Fantacalcio in modalità **Mantra**. Il contesto e la
strategia della lega sono in [`CLAUDE.md`](CLAUDE.md) e guidano ogni valutazione.

## Dati

Pipeline di raccolta dati (Serie A, da Fantacalcio.it — solo pagine **pubbliche**):

| Script | Cosa fa | Output |
|--------|---------|--------|
| `scripts/estrai_quotazioni.py` | Quotazioni asta 2026/27 (Classic + Mantra, ruoli multiruolo) | `data/quotazioni_fantacalcio.csv` |
| `scripts/estrai_statistiche.py` | Statistiche storiche multi-stagione (PV, MV, fantamedia, gol, assist…) | `data/statistiche_seriea.csv` |
| `scripts/estrai_infortuni.py` | Infortunati/indisponibili (testo narrativo + data aggiornamento) | `data/infortuni_seriea.csv` |
| `scripts/unisci_dataset.py` | Unisce quotazioni + storico per `player_id`, aggiunge colonne calcolate e forza squadra | `data/dataset_unificato.csv` |
| `scripts/ranking_reparto.py` | Classifica per reparto (por/dif/cen/att) secondo il CLAUDE.md | stampa a schermo / `--csv` |
| `scripts/genera_lista.py` | Lista Excel filtrabile (valutazione 1-20 per reparto, infortuni) | `lista_giocatori_<data>.xlsx` |
| `scripts/invia_report.py` | Genera la lista e la invia via email (Gmail SMTP) — vedi `docs/REPORT_EMAIL.md` | email con allegato |
| `scripts/genera_json.py` | Converte il dataset in JSON pulito per la pubblicazione | `build/dati.json` |

Dato statico di supporto: `data/classifiche_squadre.csv` = posizioni finali di
Serie A delle ultime 3 stagioni (fonte: Wikipedia). Usato per la colonna
`pos_media_squadra` (posizione media della squadra; **20 = stagione non in
Serie A**, proxy di fascia bassa) e per il fattore "forza squadra" dei portieri.

Rigenerare tutto:

```bash
python3 scripts/estrai_quotazioni.py
python3 scripts/estrai_statistiche.py            # default: 2025-26, 2024-25, 2023-24
python3 scripts/unisci_dataset.py
```

Nessuna dipendenza esterna: bastano Python 3 e la libreria standard.

### Note su fonti e correttezza

- **Fonte:** pagine pubbliche `quotazioni-fantacalcio` e `statistiche-serie-a` di
  Fantacalcio.it. I dati sono già nell'HTML lato server, quindi **non serve login**.
- **robots.txt rispettato:** le pagine usate non sono tra quelle bloccate
  (bloccate: `/ricerca`, `/probabiliformazioniseriea`, preview, cartelle di test).
- Il pulsante "Scarica Excel" del sito è riservato agli utenti loggati (risponde
  401) e **non** viene usato.
- Lo script statistiche attende qualche secondo tra una stagione e l'altra (cortesia
  verso il server). Uso previsto: sporadico, per aggiornare il dataset — non un
  polling continuo.
- **FantaLab.it:** valutato ma rimandato; è un sito a caricamento dinamico e per ora
  Fantacalcio.it copre già quotazioni + storico. Si riprenderà solo se emergono dati
  specifici mancanti.

## Dati pubblici (GitHub Pages)

Questo repository resta **privato** (codice, `CLAUDE.md`, script). I **soli dati**
dei giocatori vengono pubblicati in un repository **pubblico separato**
`Fantacalcio-Assistant-dati` come un unico file JSON, servito via GitHub Pages.

**URL pubblico del JSON** (l'unico pensato per essere condiviso con strumenti
esterni — pagina web, bot Telegram, ecc.):

```
https://andreaorlandi29-sudo.github.io/Fantacalcio-Assistant-dati/dati.json
```

- Contiene solo dati: nome, squadra, ruoli, quotazioni/FVM (Mantra e Classic),
  statistiche e trend per stagione, indicatori calcolati (inclusa la
  **valutazione 1-20** per reparto, la stessa dell'Excel), stato infortunio.
  Nessun codice o strategia.
- Aggiornato automaticamente: lo step 7 del workflow giornaliero genera il JSON
  (`scripts/genera_json.py`) e lo pusha nel repo pubblico (solo se cambia).
- Setup e manutenzione: vedi `docs/DATI_PUBBLICI.md`.

## Bot Telegram (Claude API)

Bot conversazionale: i messaggi Telegram vengono inoltrati a Claude via API.
Claude ragiona con la strategia del `CLAUDE.md` (system prompt) e interroga i
nostri dati tramite tre strumenti (`bot/tools.py`): classifica per reparto,
ricerca filtrata, scheda/confronto giocatori.

```
bot/
  tools.py         strumenti che Claude puo' chiamare sui dati
  agent.py         loop Claude API (system prompt = CLAUDE.md + tool use)
  telegram_bot.py  bot Telegram long-polling (solo testo)
  dry_run.py       prova locale dell'agente senza Telegram
```

### Configurazione sicura dei segreti
1. `cp .env.example .env`
2. Riempi `TELEGRAM_BOT_TOKEN` (da @BotFather) e `ANTHROPIC_API_KEY`.
3. `.env` e' escluso da git (`.gitignore`): non verra' mai committato. I segreti
   sono letti come variabili d'ambiente, mai scritti nel codice.

### Avvio
```bash
pip install -r requirements.txt
set -a; . ./.env; set +a          # carica le variabili d'ambiente dal .env
python3 -m bot.dry_run "i migliori 10 difensori"   # prova senza Telegram
python3 -m bot.telegram_bot                         # avvia il bot Telegram
```

### Chiave di unione

I dataset si uniscono su `player_id`, l'ID univoco del giocatore su Fantacalcio.it
(stabile tra stagioni, indipendente da nome e cambio squadra).
