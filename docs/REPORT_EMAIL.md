# Report giornaliero via email (lista Excel)

Ogni mattina il workflow `Aggiorna dati Fantacalcio` genera un file Excel
filtrabile con tutti i giocatori e lo invia via email come allegato.

- Generazione: `scripts/genera_lista.py` → `lista_giocatori_<data>.xlsx`
  - Colonne: Calciatore, Ruolo/i, Squadra, Valutazione (1-20), Situazione infortuni
  - Autofilter attivo + intestazione congelata
  - Valutazione 1-20 normalizzata **per reparto** riusando `ranking_reparto.py`;
    le scommesse (senza storico) hanno stima prudente e prefisso 🎲; gli
    infortunati sono marcati ⚠️ con dettaglio e data.
- Invio: `scripts/invia_report.py` (SMTP Gmail con App Password).
- Orario: cron `0 8 * * *` UTC = **10:00 ora italiana d'estate (CEST)**. Da fine
  ottobre (ora solare) diventa 09:00 italiane: per riavere le 10:00 in inverno,
  cambiare il cron in `0 9 * * *`.

## Perché Gmail SMTP (e alternative)
- **Gmail + App Password** (scelta usata): nessun servizio terzo da registrare,
  nessun dominio da configurare. Serve solo generare una App Password. Ideale
  per un invio a te stesso, poche email al giorno.
- **Alternative** (gratuite ma più configurazione): Resend / SendGrid free tier —
  migliore deliverability e mittente "professionale", ma richiedono account,
  verifica dominio/mittente e una API key. Non necessarie per questo caso d'uso.

## Cosa devi fare TU: generare la Google App Password
Serve un account Google con la **verifica in due passaggi attiva** (obbligatoria
per creare App Password).

1. Vai su https://myaccount.google.com/security
2. Attiva **Verifica in due passaggi** (se non è già attiva) e completala.
3. Sempre nella Sicurezza, apri **Password per le app**
   (link diretto: https://myaccount.google.com/apppasswords).
4. Dai un nome all'app (es. `Fantacalcio GitHub`) e crea.
5. Google mostra una password di **16 caratteri**: copiala (la vedi una volta sola).

## Impostare i secret su GitHub
Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.
Crea questi tre secret:

| Nome | Valore |
|------|--------|
| `GMAIL_ADDRESS` | il tuo indirizzo Gmail (mittente) |
| `GMAIL_APP_PASSWORD` | la App Password di 16 caratteri (senza spazi) |
| `EMAIL_TO` | l'indirizzo destinatario (può essere lo stesso Gmail) |

## Testare subito (senza aspettare le 10:00)
1. Imposta i tre secret sopra.
2. Repo → **Actions** → **Aggiorna dati Fantacalcio** → **Run workflow** (branch main).
3. A fine run controlla la tua casella: deve arrivare l'email con l'allegato
   `lista_giocatori_<data>.xlsx`. Se il run è rosso, apri lo step
   "6) Genera e invia la lista via email" per il log dell'errore.

Nota: se un secret manca o è errato, lo step fallisce (job rosso) e ricevi la
notifica di GitHub — non fallisce in silenzio.
