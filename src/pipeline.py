"""End-to-end pipeline orchestration: normalize -> dedup -> score (PRD §15, §62 Step 10-11).

Deliberately split from I/O: run_pipeline_core() takes plain lists in, returns plain
lists out, so the whole collect->normalize->dedup->score sequencing is testable without
touching Google Sheets. sheets_io.py (separate module) does the actual Sheet reads/writes
around this function.

Pilot Slice status-flow simplification (documented, not silent): PRD §14a's full state
machine is New -> Enriched -> Scored -> Ready_For_Review. Since SRC-01 already returns
contact/enrichment fields directly (no separate enrichment API call needed, unlike
SRC-02/03 which would need a real enrichment step) and AI classification is out of scope
for the pilot, a normalized+deduped lead goes straight from New to Ready_For_Review in
one step here, skipping the intermediate Enriched/Scored states as separate persisted
transitions. Status_History still isn't populated by this pilot script (§14 Secondary
entity) -- that's flagged as a gap for the ~Dec 4 full MVP continuation, not implemented
here since it would need real Sheet round-trips this pilot's manual-run flow doesn't
otherwise require yet.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any

import deduplicate as dedup
import normalize
import score as scoring

SOURCE_ID = "SRC-01"  # the only source active in the Pilot Slice (§46a)


def generate_evidence_id(existing_evidence: list[dict[str, Any]]) -> str:
    # Same pattern as deduplicate.generate_lead_id: scan existing IDs, take the max
    # numeric suffix, add one. Kept separate since Evidence_ID and Lead_ID are
    # independent sequences (E-000001 vs L-000001).
    max_n = 0
    for row in existing_evidence:
        match = re.match(r"E-(\d+)$", row.get("Evidence_ID", "") or "")
        if match:
            max_n = max(max_n, int(match.group(1)))
    return f"E-{max_n + 1:06d}"


def _build_evidence_row(candidate: dict[str, Any], matched_lead: dict[str, Any], existing_evidence: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    # Builds one Evidence_Log row for an exact-duplicate merge (AC-004.1: append
    # evidence to the existing Lead rather than creating a new row).
    row = {
        "Evidence_ID": generate_evidence_id(existing_evidence),
        "Lead_ID": matched_lead.get("Lead_ID"),        # which existing lead this evidence belongs to
        "Source_ID": SOURCE_ID,
        "Source_URL": candidate.get("Source_URL"),     # link back to where this signal was observed
        "Retrieved_At": now.isoformat(),
        "Raw_Snippet": candidate.get("Source_Evidence"),  # human-readable summary of the raw signal
    }
    existing_evidence.append(row)  # so a second merge in the same batch gets the next ID, not a duplicate one
    return row


def run_pipeline_core(
    raw_records: list[dict[str, Any]],
    existing_leads: list[dict[str, Any]],
    existing_evidence: list[dict[str, Any]] | None = None,
    today: date | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Runs normalize -> dedup -> score over one collector's raw output.

    Returns:
        {
          "new_leads": [...]            -- new Lead rows to append (Ready_For_Review or Incomplete)
          "evidence_appends": [...]     -- Evidence_Log rows to append for exact-duplicate merges
          "possible_duplicates": [...]  -- held for human review, NOT written to the Lead tab (AC-004.2)
        }
    """
    now = datetime.now(timezone.utc)
    # Copy so this function never mutates the caller's existing_evidence list in place.
    existing_evidence = list(existing_evidence or [])

    # Stage 1: raw collector output -> canonical Lead-shaped dicts (Status=New or Incomplete).
    normalized = normalize.normalize_batch(raw_records, source_id=SOURCE_ID)
    # Stage 2: classify each normalized lead against what's already in the Sheet.
    dedup_result = dedup.dedup_batch(normalized, existing_leads)

    new_leads: list[dict[str, Any]] = []
    for lead in dedup_result["new"]:
        lead = dict(lead)  # copy before mutating, since dedup_batch's "new" list is reused elsewhere
        if lead.get("Status") == "New":
            # Only score complete leads -- an Incomplete one has nothing meaningful to
            # score yet (§8 failure path: excluded from scoring until enriched/completed).
            score_fields = scoring.score_lead(lead, today=today)
            lead.update(score_fields)
            lead["Status"] = "Ready_For_Review"  # see module docstring for the state-flow simplification
        lead["Updated_At"] = now.isoformat()
        new_leads.append(lead)

    # Stage 3: exact-duplicate candidates become Evidence_Log rows, not new Lead rows.
    evidence_appends = [
        _build_evidence_row(candidate, matched_lead, existing_evidence, now)
        for candidate, matched_lead in dedup_result["exact_duplicates"]
    ]

    # Stage 4: fuzzy-matched candidates are summarized for a human to resolve manually --
    # never written to the Sheet automatically (AC-004.2).
    possible_duplicates = [
        {
            "candidate_name": candidate.get("Lead_Name"),
            "candidate_address": candidate.get("Address"),
            "matched_lead_id": matched_lead.get("Lead_ID"),
            "similarity_score": similarity,
        }
        for candidate, matched_lead, similarity in dedup_result["possible_duplicates"]
    ]

    return {
        "new_leads": new_leads,
        "evidence_appends": evidence_appends,
        "possible_duplicates": possible_duplicates,
    }
