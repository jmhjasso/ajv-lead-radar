# AJV Lead Radar — Pilot Slice

AI-assisted commercial cleaning lead discovery for AJV Cleaning (Northwest Arkansas).
Full product spec: `AJV_Cleaning_PRD_v0.2.md` (one level up, in `Leads Automation/`).

**Current milestone:** Pilot Slice, target Oct 9, 2026 (PRD §46a). One source (Google Places
API), full normalize → dedup → score pipeline, manual-run, Google Sheets as the datastore and
review queue. See `PLAN.md` for the step-by-step build sequence and `docs/` for setup guides.

## Status

Build in progress. See `docs/handoff.md` (added at Step 8) for the Pilot Slice gate result
once the pipeline is running end-to-end.

## Directory structure

```
/src            → normalize.py, deduplicate.py, score.py, collector_src01.py (Pilot Slice)
/tests          → pytest suite + /tests/fixtures (sample records)
/config         → mappings/<source_id>.json, scoring_weights.json
/docs           → setup guides, runbook, handoff notes
/prompts        → reserved for AI classification (stretch goal, PRD §17/§19)
/workflows      → n8n workflow JSON exports
/data           → local fixtures only — never real lead data (see .gitignore)
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -v
```

Secrets (Google Places API key, Google Sheets credentials) go in a local `.env` file —
never committed (see `.gitignore`). See `docs/setup.md` for exact steps.
