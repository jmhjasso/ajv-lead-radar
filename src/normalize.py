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

MAPPINGS_DIR = Path(__file__).parent.parent / "config" / "mappings"

_ZIP_RE = re.compile(r"\b\d{5}\b")


def load_mapping(source_id: str) -> dict[str, Any]:
    """Mapping filenames drop the hyphen, e.g. Source_ID 'SRC-01' -> config/mappings/src01.json."""
    filename = source_id.lower().replace("-", "")
    path = MAPPINGS_DIR / f"{filename}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_street_address(formatted_address: str | None) -> str:
    """Google's formattedAddress is 'street, city, state zip, country' -- the street
    portion is everything before the first comma."""
    if not formatted_address:
        return ""
    return formatted_address.split(",")[0].strip()


def parse_zip(formatted_address: str | None) -> str:
    if not formatted_address:
        return ""
    match = _ZIP_RE.search(formatted_address)
    return match.group(0) if match else ""


def build_source_evidence(raw: dict[str, Any]) -> str:
    reviews = raw.get("user_rating_count", 0)
    category = raw.get("property_type", "unknown category")
    observed = raw.get("retrieved_at", "")
    return f"New Places listing, {reviews} review(s), category '{category}', observed {observed}"


def normalize_record(
    raw: dict[str, Any], mapping: dict[str, Any], now: datetime | None = None
) -> dict[str, Any]:
    """Maps one raw SRC-01 record to a canonical (pre-Lead_ID) Lead dict."""
    now = now or datetime.now(timezone.utc)
    today_iso = now.date().isoformat()

    lead: dict[str, Any] = {}

    for raw_field, lead_field in mapping["field_map"].items():
        lead[lead_field] = raw.get(raw_field)

    lead.update(mapping["fixed_fields"])

    signal_id = lead["Signal_ID"]
    lead["Recommended_Service"] = mapping["signal_to_recommended_service"].get(signal_id)

    formatted_address = raw.get("formatted_address")
    lead["Address"] = parse_street_address(formatted_address)
    lead["ZIP"] = parse_zip(formatted_address)

    lead["Discovered_Date"] = today_iso
    lead["Signal_Date"] = today_iso  # SIG-03 has no independent date source (§12)
    lead["Source_Evidence"] = build_source_evidence(raw)

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

    lead["Last_Contacted"] = None
    lead["Next_Action"] = None
    lead["Estimated_Value"] = None
    lead["Notes"] = None
    lead["Rejection_Reason"] = None

    lead["Created_At"] = now.isoformat()
    lead["Updated_At"] = now.isoformat()

    missing = [f for f in REQUIRED_FIELDS if not lead.get(f)]
    lead["Status"] = "Incomplete" if missing else "New"
    lead["_missing_fields"] = missing  # internal diagnostic, not a Lead schema column

    return lead


def normalize_batch(
    raw_records: list[dict[str, Any]], source_id: str = "SRC-01"
) -> list[dict[str, Any]]:
    mapping = load_mapping(source_id)
    return [normalize_record(raw, mapping) for raw in raw_records]
