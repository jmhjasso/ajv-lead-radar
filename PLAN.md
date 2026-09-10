# AJV Lead Radar — Execution Plan (Pilot Slice, target: Oct 9, 2026)

## Context

The attached PRD (`AJV_Cleaning_PRD_v0.2.md`) already defines a full 3-source commercial
lead-generation MVP, but its own §46a ("Time-Boxed Reality Check") runs the arithmetic
against the real constraint — Chuy building this solo, ~3 hrs/day, from today (2026-09-10)
to **Oct 9, 2026** — and concludes the full 3-source MVP needs ~112–129 hours against
~60–65 realistic hours available. The PRD's own answer is not to cut corners on the full
MVP; it's to commit to a smaller, real deliverable first: the **Pilot Slice**.

This plan operationalizes §46a into an actual build sequence: one source (Google Places),
the full core pipeline (normalize → dedup → score), a real review tab, and nothing else —
by Oct 9. This is not a compromise invented for this plan; it is the PRD's own documented
recommendation (§46a, §47 Phase 1, §65 "Recommended First Engineering Task"). Everything
deferred here is deferred *in the PRD itself*, not by this plan.

**Why this matters:** the PRD is unusually rigorous — every requirement traces through
acceptance criteria, test specs, and a scoring model with a worked example. The job here is
to follow that existing design faithfully rather than re-deriving or reinterpreting it. PRD
section numbers are cited throughout so every step can be cross-checked against the source
document.

**Environment decisions confirmed with Chuy before this plan was finalized:**
- **Local project folder:** this repo, next to the PRD.
- **n8n:** Chuy already has a working n8n Cloud instance (`lab10builders.app.n8n.cloud`) —
  no new n8n subscription needed. This resolves PRD risk R-005/assumption A-006: infra cost
  is likely already ~$0 incremental for this project, which materially helps the <$10/month
  target (NFR-001).
- **GitHub:** private repo under Chuy's personal GitHub account (resolves A-001 to "personal,"
  not an AJV org).

## How execution works

Per the PRD's own operating rules (§63 Who Does What, §65 Work/Cowork Operating Instructions,
§64 Command Execution Safety):

- Code, tests, config, prompts, and docs are written and run directly (pytest, scripts, git)
  without waiting for permission on routine/reversible actions.
- Before each deliverable (a step below), what's about to be built and why is explained in
  plain language first.
- After each deliverable, what was produced (files, test output) and what it proves is shown
  before moving to the next step.
- Anything that needs Chuy specifically — creating an account, entering a payment method,
  logging into n8n/Google Cloud/OpenRouter, approving a production activation — stops and
  hands over exact instructions. This is the PRD's explicit boundary (§65).
- No destructive or irreversible action happens without stating what/risk/rollback first (§64)
  and getting a go-ahead.

## What's being built by Oct 9 (the Pilot Slice, per PRD §46a)

| In scope | Explicitly out of scope for Oct 9 (deferred to post-Oct-9 continuation toward the ~Dec 4 full MVP, PRD §46a/§47 Phase 2) |
|---|---|
| One lead source: **SRC-01 Google Places API** only | SRC-02 (city permit data) and SRC-03 (Chamber announcements) |
| Manual/on-demand pipeline run | Scheduled/unattended cron execution, failure alerting (FR-016), cost-threshold alerting (FR-017) |
| Normalization engine, fully tested | — |
| Deduplication engine (hash + fuzzy match), fully tested | — |
| Deterministic lead scoring engine (§20 weighted model), fully tested | AI classification (§17 AI-01/02) — **stretch goal only** |
| Leads stored in Google Sheets, a basic review tab (FR-012/013) | Outreach drafting automation (FR-011) — Chuy writes the opening line manually for the pilot |
| Evidence trail per lead (source, URL, timestamp) | Full audit dashboard, weekly digest (FR-025) |
| Manual ToS check for SRC-01 only | Full compliance review across all sources |

**Pilot Slice acceptance gate (PRD §46a, replaces §46 for this milestone only):**
≥ 10 real leads produced from SRC-01 across the 8 priority NWA cities; the dedup engine has
zero false-negatives on a 10-record manual spot-check; every lead shows its `Score_Breakdown`;
Chuy judges at least half of the top-scored leads "plausible to call." This is a proof point,
not the full MVP gate — §46 still governs when the product is actually "done."

## Week-by-week schedule (from PRD §46a)

| Week | Dates | Focus | Hours |
|---|---|---|---|
| 1 | Sep 10–16 | Repo + dev environment; datastore schema in Google Sheets | ~12 |
| 2 | Sep 17–23 | SRC-01 collector; normalization service + tests | ~12 |
| 3 | Sep 24–30 | Deduplication engine + tests; deterministic scoring engine + tests | ~13 |
| 4 | Oct 1–7 | End-to-end wiring; review tab; first real run against live NWA data; fix what breaks | ~14 |
| 5 | Oct 8–9 | Manual QA against the Pilot Slice gate; fix list; hand off for review | ~4–6 |

## Step-by-step build sequence

**Step 1 — Repo & dev environment (PRD §27, §62 Step 1–2)** — directory scaffold, `.gitignore`,
`requirements.txt`, README, git init; GitHub repo creation (Chuy, personal account).

**Step 2 — Datastore schema (PRD §14, §62 Step 3)** — Google Sheets tabs (`Lead`,
`Source_Config`, `Evidence_Log`, `Status_History`) matching §14 exactly.

**Step 3 — SRC-01 collector (PRD §12 SRC-01, §16, §62 Step 4)** — Google Places API collector
for the 8 priority NWA cities × approved commercial categories (§10 FR-002), SIG-03 heuristic
(§13). Requires Chuy to create a Google Cloud project + API key first.

**Step 4 — Normalization service (PRD §14, §16, §21 US-002, §62 Step 5)** — `src/normalize.py`
+ per-source mapping config + `Status=Incomplete` fallback (AC-003.1).

**Step 5 — Deduplication engine (PRD §16, §21 US-003, §62 Step 6)** — `src/deduplicate.py`,
hash match + fuzzy-match flagging (AC-004.1/.2).

**Step 6 — Deterministic scoring engine (PRD §20, §62 Step 9)** — `src/score.py`, exact
weighted model, reproduces §20's worked example (score 91 → Hot) plus threshold boundary
tests.

**Step 7 — End-to-end wiring + review tab (PRD §15, §62 Step 10–11)** — collect → normalize →
dedup → score → write-to-Sheet, sorted review view (FR-012), first real run against live data.

**Step 8 — QA against the Pilot Slice gate + handoff (PRD §46a gate, §62 Step 17–18 scaled
down)** — full pytest run, manual dedup spot-check, `Score_Breakdown` completeness check,
Chuy's "plausible to call" review, handoff doc with what's next toward ~Dec 4 full MVP.

**Stretch (only if hours remain):** AI classification (§17 AI-01/02) via OpenRouter.

## Explicitly not happening in this pass

No automated/scheduled execution, no outreach sending, no SRC-02/SRC-03, no AI drafting, no
account/payment/credential actions on Chuy's behalf, no production go-live.

## Verification approach

- Every Python module gets a `pytest` suite, run and shown at each step.
- Step 3's collector validated against a real Google Places API key (small live smoke test).
- Step 7's end-to-end run produces real leads from real NWA data.
- Step 8 checks the Pilot Slice gate criteria one by one before declaring "done for Oct 9."
