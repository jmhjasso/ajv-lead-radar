# Google Cloud Setup (Chuy — requires your login/billing, PRD §65 human-only boundary)

One Google Cloud project covers both credentials the Pilot Slice needs: a **Places API key**
(Step 3, collector) and a **service account** for Sheets access (Step 2, datastore). Do this
once, in order.

## 1. Create the Google Cloud project

1. Go to https://console.cloud.google.com/projectcreate
2. Project name: `ajv-lead-radar` (or similar — doesn't matter, just keep it identifiable)
3. Billing account: attach one. Google requires a card on file even for free-tier usage
   (PRD assumption A-004) — Places API has a recurring free monthly credit that should cover
   Pilot Slice query volume, but this is the point where you should also set a **budget
   alert** (see step 5) so nothing surprises you.

## 2. Enable the two APIs this project needs

1. Go to https://console.cloud.google.com/apis/library
2. Search for and **Enable**: `Places API (New)`
3. Search for and **Enable**: `Google Sheets API`

## 3. Create the Places API key (for Step 3, the collector)

1. Go to https://console.cloud.google.com/apis/credentials
2. **Create Credentials → API key**
3. Click the new key → **Restrict key**:
   - Application restrictions: None needed for local/server use (or "IP addresses" if you
     want to lock it to your machine — optional for the pilot)
   - API restrictions: select "Restrict key" → check **Places API (New)** only
4. Copy the key value. **Do not paste it into chat or commit it to git.** It goes in a local
   `.env` file (see step 6).

## 4. Create the service account (for Step 2, Sheets access)

1. Still in https://console.cloud.google.com/apis/credentials
2. **Create Credentials → Service account**
3. Name: `ajv-lead-radar-sheets`, no special roles needed at the project level (default is
   fine — access is granted per-spreadsheet by sharing, not by IAM role)
4. Once created, click the service account → **Keys** tab → **Add Key → Create new key → JSON**
5. This downloads a JSON file (something like `ajv-lead-radar-xxxxx.json`). This is a secret
   credential — treat it like a password.
6. Open the JSON file and copy the `"client_email"` value (looks like
   `ajv-lead-radar-sheets@ajv-lead-radar.iam.gserviceaccount.com`) — you'll need it next.

## 5. Create the blank spreadsheet and share it with the service account

1. Go to https://sheets.google.com, create a new blank spreadsheet, name it `AJV Lead Radar`.
2. Click **Share**, paste in the service account email from step 4.6, give it **Editor**
   access, uncheck "notify people" (it's not a real inbox).
3. Copy the spreadsheet ID from the URL — the long string between `/d/` and `/edit`, e.g.
   `https://docs.google.com/spreadsheets/d/`**`1AbCdEfGhIjKlMnOpQrStUvWxYz`**`/edit`

## 6. (Recommended) Set a budget alert

1. Go to https://console.cloud.google.com/billing/budgets
2. Create a budget, e.g. $10/month, with an alert at 50%/90%/100% — matches PRD NFR-001's
   <$10/month target and gives you an early warning independent of anything this pipeline
   tracks internally.

## 7. Where credentials go locally (never in git — enforced by `.gitignore`)

Once you have the three secrets (Places API key, service-account JSON file, spreadsheet ID),
tell me and I'll set up a local `.env` file (already gitignored) plus point the service-account
JSON at `config/credentials.json` (also gitignored) — you'll paste/save the values yourself so
they never pass through chat. I'll then write the setup script that provisions the 4 tabs.

## What to send back when ready

You don't need to paste secret values into chat. Just tell me:
- "Places API key created" (I'll ask you to save it into `.env` yourself, I'll give you the
  exact line to add)
- "Service account JSON downloaded to [wherever you saved it]"
- The spreadsheet ID (this one's not secret — just an identifier — safe to share directly)
