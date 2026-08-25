# Dati pubblici via GitHub Pages (repo separato)

Il repo principale è **privato**. Per pubblicare **solo il JSON dei dati**
usiamo un secondo repository **pubblico** con GitHub Pages (gratis, perché il
repo che serve le Pages è pubblico). Il workflow giornaliero del repo privato
genera il JSON e lo pusha in quello pubblico.

Architettura:

```
repo PRIVATO (questo)                 repo PUBBLICO (Fantacalcio-Assistant-dati)
  workflow giornaliero                  main:
   ├─ aggiorna data/                       ├─ dati.json   ← servito da Pages
   └─ step 7: genera JSON  ── PAT ─▶        └─ index.html
```

## Passi manuali (una tantum)

### 1) Crea il repository pubblico dei dati
- GitHub → **New repository**
- **Name**: `Fantacalcio-Assistant-dati` (esattamente questo: l'URL e il workflow
  lo assumono; se usi un altro nome, imposta la variabile `DATA_REPO` — vedi sotto)
- **Public**
- Spunta **Add a README** (serve un commit iniziale sul branch `main`)
- **Create repository**

### 2) Abilita GitHub Pages sul repo pubblico
- Nel repo pubblico → **Settings** → **Pages**
- **Source**: *Deploy from a branch*
- **Branch**: `main`, cartella **/ (root)** → **Save**
- Dopo il primo aggiornamento, il file sarà su
  `https://<utente>.github.io/Fantacalcio-Assistant-dati/dati.json`

### 3) Crea un token (PAT) per far scrivere il workflow sul repo pubblico
Il `GITHUB_TOKEN` del repo privato non può scrivere su un altro repo: serve un
Personal Access Token.
- GitHub → **Settings** (del tuo account) → **Developer settings** →
  **Personal access tokens** → **Fine-grained tokens** → **Generate new token**
- **Resource owner**: il tuo utente
- **Repository access**: *Only select repositories* → scegli
  `Fantacalcio-Assistant-dati`
- **Permissions** → **Repository permissions** → **Contents**: **Read and write**
- Genera e **copia** il token.

### 4) Salva il token come secret nel repo PRIVATO
- Repo privato → **Settings** → **Secrets and variables** → **Actions** →
  **New repository secret**
- **Name**: `DATA_REPO_TOKEN` · **Value**: il PAT copiato → **Add secret**
- (Facoltativo) Se hai usato un nome repo diverso, aggiungi anche una
  **Variable** (tab *Variables*) `DATA_REPO` = `tuo-utente/tuo-repo-dati`.

### 5) Primo popolamento
- Repo privato → **Actions** → **Aggiorna dati Fantacalcio** → **Run workflow**.
- Lo step **7) Pubblica dati.json sul repo pubblico** clona il repo pubblico,
  copia `dati.json` + `index.html` e li pusha (solo se cambia qualcosa).
- Apri l'URL pubblico: dopo 1-2 minuti (build Pages) vedrai il JSON.

## Note
- Finché `DATA_REPO_TOKEN` non è impostato, lo step 7 **si salta senza errori**
  (non fa fallire il workflow).
- Nessun commit inutile: lo step committa sul repo pubblico solo se il JSON
  effettivamente cambia.
- Cosa è pubblico: **solo** `dati.json` (e la `index.html` di cortesia). Codice,
  `CLAUDE.md`, script, credenziali restano nel repo privato.
