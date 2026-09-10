"""Normalization service: raw source record -> canonical Lead schema (PRD §14).

PRD refs: §16 Normalization Service, §21 US-002 (FR-003), AC-003.1, §62 Step 5.

Maps a collector's raw record onto the exact Lead field set from docs/sheets_schema.md
using a per-source mapping config (config/mappings/<source_id>.json), so adding SRC-02/03
later means adding a new mapping file, not touching this module's logic.

Fields this module does NOT fill in (left blank, filled by later pipeline stages):
  - Lead_ID          -- assigned when deduplicate.py confirms this is a genuinely new lead
  - Lead_Score, Score_Breakdown, Lead_Category -- filled by score.py (Step 6)

Per AC-003.1: a missing required field never raises -- it sets Status="Incomplete" instead.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# The fields checked for AC-003.1's "missing required field -> Status=Incomplete" rule.
# Not every §14 Required=Yes column is here -- only the ones a raw record could plausibly
# be missing (Lead_ID/Created_At/etc. are always system-generated, never absent).
REQUIRED_FIELDS = [
    "Lead_Name",
    "Address",
    "City",
    "State",
    "Property_Type",
    "Lead_Source",
    "Source_URL",
    "Source_Evidence",
    "Recommended_Service",
]

# Pilot Slice placeholders (docs/sheets_schema.md "Pilot Slice notes") -- AI classification
# is out of scope until the stretch goal or Phase 2, so these fixed values keep the schema
# satisfied without a real model call.
AI_CONFIDENCE_PLACEHOLDER = 0
AI_MODEL_USED_PLACEHOLDER = "none (deterministic-only pilot)"
PROMPT_VERSION_PLACEHOLDER = "n/a"

# Where per-source mapping configs live -- one JSON file per Source_ID (§27 directory layout).
MAPPINGS_DIR = Path(__file__).parent.parent / "config" / "mappings"

# Matches any run of 5 consecutive digits -- used to pull a ZIP code out of a full
# US postal address string (good enough for the Pilot Slice's single source).
_ZIP_RE = re.compile(r"\b\d{5}\b")


def load_mapping(source_id: str) -> dict[str, Any]:
    """Mapping filenames drop the hyphen, e.g. Source_ID 'SRC-01' -> config/mappings/src01.json."""
    filename = source_id.lower().replace("-", "")  # "SRC-01" -> "src01" to match the actual filename
    path = MAPPINGS_DIR / f"{filename}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_street_address(formatted_address: str | None) -> str:
    """Google's formattedAddress is 'street, city, state zip, country' -- the street
    portion is everything before the first comma."""
    if not formatted_address:
        return ""
    # split(",")[0] grabs just the first comma-delimited segment (the street line);
    # .strip() removes any leading/trailing whitespace left over from the split.
    return formatted_address.split(",")[0].strip()


def parse_zip(formatted_address: str | None) -> str:
    if not formatted_address:
        return ""
    # Search the whole address string for the first 5-digit run -- that's the ZIP.
    match = _ZIP_RE.search(formatted_address)
    return match.group(0) if match else ""


def build_source_evidence(raw: dict[str, Any]) -> str:
    # Pulls the fields a human reviewer needs to sanity-check *why* this lead exists,
    # into one readable sentence stored in Lead.Source_Evidence (FR-009's evidence trail).
    reviews = raw.get("user_rating_count", 0)
    category = raw.get("property_type", "unknown category")
    observed = raw.get("retrieved_at", "")
    return f"New Places listing, {reviews} review(s), category '{category}', observed {observed}"


def normalize_record(
    raw: dict[str, Any], mapping: dict[str, Any], now: datetime | None = None
) -> dict[str, Any]:
    """Maps one raw SRC-01 record to a canonical (pre-Lead_ID) Lead dict."""
    # `now` is injectable so tests can pin a fixed timestamp instead of depending on
    # the wall clock (see tests/test_normalize.py's FIXED_NOW).
    now = now or datetime.now(timezone.utc)
    today_iso = now.date().isoformat()

    lead: dict[str, Any] = {}

    # field_map declares raw_record_key -> canonical_Lead_field pairs from the mapping
    # config, so a straight rename/copy doesn't need custom code per source.
    for raw_field, lead_field in mapping["field_map"].items():
        lead[lead_field] = raw.get(raw_field)

    # fixed_fields are constants for this source (e.g. State is always "AR" for SRC-01),
    # applied after the dynamic field_map so they can't be accidentally overridden by it.
    lead.update(mapping["fixed_fields"])

    # Recommended_Service is derived from which Signal_ID this source's records always
    # carry (SIG-03 for SRC-01) -- a simple deterministic lookup, no AI call needed.
    signal_id = lead["Signal_ID"]
    lead["Recommended_Service"] = mapping["signal_to_recommended_service"].get(signal_id)

    # Address/ZIP need light parsing out of Google's single formattedAddress string --
    # the Lead schema keeps them as separate columns.
    formatted_address = raw.get("formatted_address")
    lead["Address"] = parse_street_address(formatted_address)
    lead["ZIP"] = parse_zip(formatted_address)

    lead["Discovered_Date"] = today_iso     # the date this pipeline run found the record
    lead["Signal_Date"] = today_iso         # SIG-03 has no independent date source (§12)
    lead["Source_Evidence"] = build_source_evidence(raw)

    # Places doesn't expose these for a generic business listing -- left blank rather
    # than guessed, so the review queue never shows fabricated contact info.
    lead["Company"] = None
    lead["Contact_Name"] = None
    lead["Email"] = None

    # Filled by later stages -- present as keys so the Sheet's column order stays intact.
    lead["Lead_Score"] = None
    lead["Score_Breakdown"] = None
    lead["Lead_Category"] = None
    lead["AI_Confidence"] = AI_CONFIDENCE_PLACEHOLDER
    lead["AI_Model_Used"] = AI_MODEL_USED_PLACEHOLDER
    lead["Prompt_Version"] = PROMPT_VERSION_PLACEHOLDER

    # Optional, human-entered-later fields -- always start empty for a freshly
    # discovered lead.
    lead["Last_Contacted"] = None
    lead["Next_Action"] = None
    lead["Estimated_Value"] = None
    lead["Notes"] = None
    lead["Rejection_Reason"] = None

    # System timestamps -- both start equal to "now" since this row didn't exist before.
    lead["Created_At"] = now.isoformat()
    lead["Updated_At"] = now.isoformat()

    # AC-003.1: check the fields a raw record could genuinely be missing; if any are
    # empty/falsy, mark Incomplete instead of ever raising an exception.
    missing = [f for f in REQUIRED_FIELDS if not lead.get(f)]
    lead["Status"] = "Incomplete" if missing else "New"
    lead["_missing_fields"] = missing  # internal diagnostic, not a Lead schema column

    return lead


def normalize_batch(
    raw_records: list[dict[str, Any]], source_id: str = "SRC-01"
) -> list[dict[str, Any]]:
    # Loads the mapping config once, then reuses it across every record in the batch --
    # avoids re-reading the same JSON file from disk per record.
    mapping = load_mapping(source_id)
    return [normalize_record(raw, mapping) for raw in raw_records]
