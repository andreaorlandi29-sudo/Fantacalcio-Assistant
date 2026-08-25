# Storage rosa persistente (Render Key Value)

La gestione rosa live salva lo stato su un **Render Key Value** (Redis),
un servizio **separato** dal Web Service: i redeploy del bot (incluso
l'aggiornamento dati quotidiano) **non** lo cancellano.

## Perché Key Value e non Postgres
Il dato è uno solo e piccolo (la rosa come singolo JSON), con letture/scritture
banali durante l'asta. Redis = `GET`/`SET` di una chiave, zero schema/SQL.
Postgres sarebbe sovradimensionato. Caveat: il Key Value **free** è in-memory,
quindi non durevole se il servizio KV stesso viene riavviato (raro). Mitigazioni:
il bot rimanda il riepilogo rosa dopo ogni acquisto (backup in chat) e il giorno
dell'asta conviene mettere in pausa il workflow di aggiornamento dati.

## Creare e collegare il Key Value (passaggi manuali su Render)
1. Dashboard Render → **New +** → **Key Value**.
2. Impostazioni:
   - **Name**: es. `fantacalcio-rosa`
   - **Region**: la **stessa** del Web Service (così puoi usare la connessione interna)
   - **Plan**: **Free**
   - **Maxmemory policy**: lascia il default (va bene, la chiave è una sola)
   - **Create Key Value**.
3. Aperto il Key Value, copia la **Internal Connection String**
   (formato `redis://...:6379`). L'interna è preferibile: più veloce, resta
   dentro Render.
4. Vai sul **Web Service** (fantacalcio-assistant) → **Environment** → **Add
   Environment Variable**:
   - **Key**: `REDIS_URL`
   - **Value**: la Internal Connection String copiata sopra
   - **Save Changes** → il bot fa redeploy e da quel momento la rosa è attiva.

Verifica: scrivi al bot "stato rosa" — deve rispondere con budget 500, 0
giocatori. Se dice che lo storage non è configurato, `REDIS_URL` non è arrivata.

## Resettare la rosa (il giorno dell'asta / dopo i test)
Tre modi, dal più semplice:
1. **Scrivi al bot**: "resetta la rosa" (chiederà conferma, poi azzera).
2. **Da locale**: con `REDIS_URL` impostata sull'**External Connection String**
   del Key Value (`rediss://...`): `python3 -m bot.rosa_reset`.
3. **Dashboard**: dal Key Value puoi anche rigenerarlo/svuotarlo, ma i modi 1-2
   sono più rapidi.

## Come funziona (per riferimento)
- Chiave Redis: `rosa:v1`, valore = JSON `{budget_totale, acquisti:[...]}`.
- Tool dell'agente: `registra_acquisto`, `stato_rosa`, `correggi_acquisto`,
  `annulla_ultimo_acquisto`, `reset_rosa` (in `bot/tools.py` → `bot/rosa_store.py`).
- Target reparti e budget vengono dal `CLAUDE.md` (sezione "Composizione rosa").
