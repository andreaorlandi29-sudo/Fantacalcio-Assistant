# Assistente Fantacalcio Mantra

Assistente personale per il Fantacalcio in modalità **Mantra**. Il contesto e la
strategia della lega sono in [`CLAUDE.md`](CLAUDE.md) e guidano ogni valutazione.

## Dati

Pipeline di raccolta dati (Serie A, da Fantacalcio.it — solo pagine **pubbliche**):

| Script | Cosa fa | Output |
|--------|---------|--------|
| `scripts/estrai_quotazioni.py` | Quotazioni asta 2026/27 (Classic + Mantra, ruoli multiruolo) | `data/quotazioni_fantacalcio.csv` |
| `scripts/estrai_statistiche.py` | Statistiche storiche multi-stagione (PV, MV, fantamedia, gol, assist…) | `data/statistiche_seriea.csv` |
| `scripts/unisci_dataset.py` | Unisce quotazioni + storico per `player_id`, aggiunge colonne calcolate e forza squadra | `data/dataset_unificato.csv` |
| `scripts/ranking_reparto.py` | Classifica per reparto (por/dif/cen/att) secondo il CLAUDE.md | stampa a schermo / `--csv` |

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

### Chiave di unione

I dataset si uniscono su `player_id`, l'ID univoco del giocatore su Fantacalcio.it
(stabile tra stagioni, indipendente da nome e cambio squadra).
