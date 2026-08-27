# Deploy del bot su Render (piano gratuito, modalità webhook)

> **Perché Web Service e non Background Worker?** Sul piano **free** di Render i
> Background Worker non sono disponibili (solo Web Service, Static Site, Postgres,
> Key Value). Quindi usiamo un **Web Service gratuito** e trasformiamo il bot in
> **webhook**: è Telegram a inviarci i messaggi via HTTP, e il servizio si
> risveglia da solo quando arriva un messaggio.

## 0. Prerequisito
Il codice è sul branch GitHub **`claude/fantacalcio-mantra-assistant-g1utmg`**
del repo `andreaorlandi29-sudo/Fantacalcio-Assistant`. In Render sceglierai
questo branch (oppure prima fai il merge su `main`).

## 1. Crea il Web Service
1. Vai su https://dashboard.render.com → **New +** → **Web Service**.
2. **Connect GitHub** e autorizza Render ad accedere al repo
   `Fantacalcio-Assistant` (puoi limitarlo a questo solo repo).
3. Seleziona il repository, poi:
   - **Branch**: `claude/fantacalcio-mantra-assistant-g1utmg`
   - **Language / Runtime**: Python (rilevato in automatico)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**:
     `gunicorn bot.webhook:app --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT`
   - **Instance Type**: **Free**

## 2. Variabili d'ambiente (sezione "Environment")
Aggiungi queste chiavi (i valori NON vanno nel codice):

| Key | Value |
|-----|-------|
| `TELEGRAM_BOT_TOKEN` | il token del bot (BotFather) |
| `ANTHROPIC_API_KEY` | la tua chiave Anthropic |
| `WEBHOOK_SECRET` | una stringa casuale a tua scelta (es. 20+ caratteri) |
| `CLAUDE_MODEL` | `claude-sonnet-5` |
| `TELEGRAM_ALLOWED_USER_ID` | il tuo ID utente Telegram numerico (personale — non pubblicarlo) |

Note:
- **NON** impostare `PORT` (lo fornisce Render) né `RENDER_EXTERNAL_URL` (lo
  fornisce Render in automatico, e serve al bot per auto-registrare il webhook).
- Per generare un `WEBHOOK_SECRET` casuale puoi usare un password manager, oppure
  da terminale: `openssl rand -hex 20`.

> In alternativa a tutta la configurazione manuale, il repo contiene `render.yaml`
> (Blueprint): da **New + → Blueprint** Render legge quel file e precompila
> build/start command e variabili (i due segreti li inserisci comunque a mano).

## 3. Deploy
Clicca **Create Web Service**. Render fa il build e avvia il servizio.
Al primo avvio il bot **registra da solo il webhook** su Telegram usando l'URL
pubblico (`RENDER_EXTERNAL_URL`). Nei **Logs** dovresti vedere una riga tipo:
`setWebhook -> True`.

## 4. Impostare/Verificare il webhook (di norma automatico)
L'auto-registrazione dovrebbe bastare. Per **verificare** apri nel browser:

```
https://api.telegram.org/bot<TOKEN>/getWebhookInfo
```

Devi vedere `"url"` che punta a `https://<tuo-servizio>.onrender.com/webhook`.

Se per qualche motivo non fosse impostato, puoi farlo **a mano** (una volta):

```
https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<tuo-servizio>.onrender.com/webhook&secret_token=<WEBHOOK_SECRET>
```

(oppure, da terminale nel repo con le variabili caricate:
`python3 -m bot.set_webhook set https://<tuo-servizio>.onrender.com`)

## 5. Sicurezza dell'endpoint
L'endpoint `/webhook` accetta solo richieste che presentano l'header
`X-Telegram-Bot-Api-Secret-Token` uguale a `WEBHOOK_SECRET` (Telegram lo invia
ad ogni chiamata perché l'abbiamo passato in `setWebhook`). Qualsiasi altra
richiesta riceve **403**. L'URL da solo, senza il secret, non è azionabile.

## 6. Verifica finale
1. Apri l'URL del servizio nel browser: deve rispondere
   `Fantacalcio Mantra bot: attivo.`
2. Scrivi un messaggio al bot da Telegram.
   - Se il servizio era "addormentato", il **primo** messaggio richiede ~1 minuto
     (risveglio a freddo): la risposta arriva appena il servizio è su.
   - I messaggi successivi sono veloci (~10-15s con Sonnet 5).

## 7. Riavvio automatico e sleep (piano free)
- **Crash**: Render riavvia automaticamente il processo del Web Service se
  termina in modo anomalo (supervisione di processo + deploy salute). Non devi
  fare nulla.
- **Sleep**: un Web Service **free** va in sleep dopo **15 minuti senza
  richieste in ingresso** e si risveglia alla richiesta successiva. In modalità
  webhook questo va bene: il messaggio Telegram funge da "sveglia". L'unico
  effetto è il ritardo (~1 min) sul **primo** messaggio dopo un periodo di
  inattività.
- **Ore gratuite**: il piano free include 750 ore-istanza/mese, consumate solo
  mentre il servizio è sveglio; in webhook (sleep quando inattivo) ne usi molte
  meno del limite.

## Attenzione: un solo canale per volta
Webhook e polling si escludono a vicenda. Con il webhook attivo, **non** avviare
`bot.telegram_bot` (polling) altrove: Telegram rifiuterebbe il polling
(errore 409 conflict). Per tornare al polling: `python3 -m bot.set_webhook delete`.
