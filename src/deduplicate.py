"""Deduplication engine: hash match + fuzzy-match fallback (PRD §16, FR-004, §62 Step 6).

AC-004.1: exact name+address hash match -> no new Lead_ID, evidence appended to the
existing Lead instead.
AC-004.2: 75-89% fuzzy-match similarity -> flagged Possible_Duplicate for human
resolution; explicitly NOT auto-merged and NOT auto-created as a new row.

Spec gap, resolved deliberately (documented here rather than silently papered over):
PRD §14's Status enum has no "Possible_Duplicate" value, even though AC-004.2 names it.
Rather than invent a new Status value that would break the state machine defined in
§14a, this module returns possible-duplicate candidates as their own classification
bucket -- the caller (the Step 7 orchestrator) decides how to surface them for review
without writing a new Lead row automatically, matching AC-004.2's "not auto-created."

Also, since PRD leaves the 90-99% fuzzy-score band unaddressed (AC-004.2 only defines
75-89 explicitly), this module treats the whole open interval [FUZZY_LOW, 100) as
"flag for a human," since AC-004.2's principle is that anything short of an exact hash
match must never be auto-merged. Documented as an interpretation, not a silent guess.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from rapidfuzz import fuzz

FUZZY_LOW = 75  # AC-004.2 lower bound

_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_key(text: str | None) -> str:
    if not text:
        return ""
    text = text.lower()
    text = _NON_ALNUM_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def dedup_key(lead: dict[str, Any]) -> str:
    return f"{normalize_key(lead.get('Lead_Name'))}|{normalize_key(lead.get('Address'))}"


def compute_dedup_hash(lead: dict[str, Any]) -> str:
    return hashlib.sha256(dedup_key(lead).encode("utf-8")).hexdigest()


def similarity_score(candidate: dict[str, Any], existing: dict[str, Any]) -> float:
    return fuzz.token_sort_ratio(dedup_key(candidate), dedup_key(existing))


def generate_lead_id(existing_leads: list[dict[str, Any]]) -> str:
    """Next sequential L-000001-style ID based on the highest existing numeric suffix."""
    max_n = 0
    for lead in existing_leads:
        lead_id = lead.get("Lead_ID", "")
        match = re.match(r"L-(\d+)$", lead_id or "")
        if match:
            max_n = max(max_n, int(match.group(1)))
    return f"L-{max_n + 1:06d}"


def dedup_batch(
    candidates: list[dict[str, Any]], existing_leads: list[dict[str, Any]]
) -> dict[str, list[Any]]:
    """Classifies each candidate against existing_leads (plus any new leads created
    earlier in this same batch, so two candidates for the same real business within
    one collection run also get caught).

    Returns:
        {
          "new": [lead, ...]                                   -- assigned a fresh Lead_ID
          "exact_duplicates": [(candidate, matched_lead), ...]  -- append evidence only
          "possible_duplicates": [(candidate, matched_lead, score), ...]  -- held for review
        }
    """
    working_pool = list(existing_leads)
    hash_index: dict[str, dict[str, Any]] = {
        compute_dedup_hash(lead): lead for lead in working_pool
    }

    result: dict[str, list[Any]] = {
        "new": [],
        "exact_duplicates": [],
        "possible_duplicates": [],
    }

    for candidate in candidates:
        candidate_hash = compute_dedup_hash(candidate)

        if candidate_hash in hash_index:
            result["exact_duplicates"].append((candidate, hash_index[candidate_hash]))
            continue

        best_score = 0.0
        best_match: dict[str, Any] | None = None
        for existing in working_pool:
            score = similarity_score(candidate, existing)
            if score > best_score:
                best_score, best_match = score, existing

        if best_match is not None and best_score >= FUZZY_LOW:
            result["possible_duplicates"].append((candidate, best_match, best_score))
            continue

        candidate = dict(candidate)
        candidate["Lead_ID"] = generate_lead_id(working_pool)
        result["new"].append(candidate)

        working_pool.append(candidate)
        hash_index[candidate_hash] = candidate

    return result
