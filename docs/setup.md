# Google Cloud Setup (Chuy — requires your login/billing, PRD §65 human-only boundary)

One Google Cloud project covers both credentials the Pilot Slice needs: a **Places API key**
(Step 3, collector) and an **OAuth client** for Sheets access (Step 2, datastore). Do this
once, in order.

> **Note (2026-09-10):** the original version of this doc used a service-account JSON key for
> Sheets access. Many Google Cloud orgs now block service-account key creation by default
> (`iam.managed.disableServiceAccountKeyCreation` policy) — you hit that. Section 4 below uses
> an OAuth client instead: it authenticates as *your own* Google account, isn't affected by
> that policy, and is simpler for a single-user tool anyway — no separate service-account
> email to share the spreadsheet with.

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

## 2a. Complete Maps Platform project onboarding (required — easy to miss)

Enabling "Places API (New)" in the API Library is **not enough by itself**. Google Maps
Platform requires a separate one-time project setup, even when billing is already active
and the API shows as enabled. Symptom if you skip this: every Places API call returns
`403 PERMISSION_DENIED` with no more specific message, regardless of key restrictions or
billing status — this cost real debugging time on 2026-09-10, so don't skip it.

1. Go to https://console.cloud.google.com/google/maps-apis/overview?project=<your-project-id>
2. If you see a red banner reading **"Maps project needed to use Maps APIs"**, click
   **"Set up Maps Project"** and follow it through.
3. You may also hit a "Welcome" survey (industry/use-case questions) — click **"Skip for
   now"**, it's cosmetic and doesn't affect permissions.
4. Any API key created/restricted *after* this onboarding step completes will work; keys
   created before it may need to be re-saved (open the key, re-click the restriction
   save button) once onboarding is done.

## 3. Create the Places API key (for Step 3, the collector)

1. Go to https://console.cloud.google.com/apis/credentials
2. **Create Credentials → API key**
3. Click the new key → **Restrict key**:
   - Application restrictions: None needed for local/server use (or "IP addresses" if you
     want to lock it to your machine — optional for the pilot)
   - API restrictions: select "Restrict key" → check **Places API (New)** only
4. Copy the key value. **Do not paste it into chat or commit it to git.** It goes in a local
   `.env` file (see step 6).

## 4. Create an OAuth client (for Step 2, Sheets access — replaces the blocked service account)

1. First, configure the consent screen if you haven't already: go to
   https://console.cloud.google.com/auth/overview, choose **External** user type (fine for
   a personal/small-business tool not going through Google review), fill in an app name
   (`AJV Lead Radar`) and your email as support/contact. Under **Test users**, add your own
   Google account email — this keeps the app in "Testing" mode, which is all a solo tool
   needs (no Google review required, just a warning screen you'll click through once).
2. Go to https://console.cloud.google.com/apis/credentials
3. **Create Credentials → OAuth client ID**
4. Application type: **Desktop app**. Name: `ajv-lead-radar-desktop`.
5. Click **Create**, then **Download JSON** on the client you just created. This file
   (something like `client_secret_....json`) is *not* a service-account key, so it isn't
   affected by the org policy that blocked step 4 before. It's still a credential — treat it
   like a password, never commit it.
6. Save it somewhere on your machine — you'll tell me the path, not paste its contents.

The first time the pipeline actually calls the Sheets API, it will open a browser window
asking you to log into the Google account you added as a test user and approve access — a
one-time step that stores a local token afterward (also gitignored) so you won't need to
re-approve every run.

## 5. Create the blank spreadsheet in your own Drive

1. Go to https://sheets.google.com, create a new blank spreadsheet, name it `AJV Lead Radar`.
2. No sharing step needed — since we're authenticating as you via OAuth (not a service
   account), the pipeline will already have access to anything in your own Drive.
3. Copy the spreadsheet ID from the URL — the long string between `/d/` and `/edit`, e.g.
   `https://docs.google.com/spreadsheets/d/`**`1AbCdEfGhIjKlMnOpQrStUvWxYz`**`/edit`

## 6. (Recommended) Set a budget alert

1. Go to https://console.cloud.google.com/billing/budgets
2. Create a budget, e.g. $10/month, with an alert at 50%/90%/100% — matches PRD NFR-001's
   <$10/month target and gives you an early warning independent of anything this pipeline
   tracks internally.

## 7. Where credentials go locally (never in git — enforced by `.gitignore`)

Once you have the three items (Places API key, OAuth client JSON file, spreadsheet ID), tell
me and I'll set up a local `.env` file (already gitignored) plus point the OAuth client JSON
at `config/credentials.json` (also gitignored) — you'll paste/save the values yourself so they
never pass through chat. I'll then write the setup script that provisions the 4 tabs, which
will trigger the one-time browser login/approval described in step 4.

## What to send back when ready

You don't need to paste secret values into chat. Just tell me:
- "Places API key created" (I'll ask you to save it into `.env` yourself, I'll give you the
  exact line to add)
- "OAuth client JSON downloaded to [wherever you saved it]"
- The spreadsheet ID (this one's not secret — just an identifier — safe to share directly)
