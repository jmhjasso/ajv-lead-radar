"""Deterministic lead scoring engine (PRD §20, FR-007/FR-008, §62 Step 9).

Fully explainable, Python-computed, no ML/LLM involvement (§20 design principle) --
every point in Score_Breakdown traces to a named feature.

Documented interpretation (PRD §20 doesn't fully specify, flagged rather than guessed):
"Data completeness" says "required fields populated / required fields total" but the
canonical Required=Yes field list in §14 is dominated by fields normalize.py already
guarantees are 100% populated before a lead reaches scoring (Lead_Name, Address, City,
State, ... -- Status would be "Incomplete" and excluded from scoring otherwise, per
§14a). Using that full list would make this feature a near-constant, not a
discriminator. §20's own rationale text calls out "phone/website/address detail" as
what makes a lead "harder to act on" -- so this module scopes completeness to the
optional, genuinely-variable contact/identity fields instead: Phone, Website, Email,
ZIP, Contact_Name, Company.
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any

# §13 signal strength weights, including SIG-08's near-floor weight (PRD v0.2).
SIGNAL_STRENGTH = {
    "SIG-01": 40,
    "SIG-02": 35,
    "SIG-06": 30,
    "SIG-07": 28,
    "SIG-03": 20,
    "SIG-04": 10,
    "SIG-08": 3,
}

# §13 Expiration Period per signal, used as the recency-decay denominator.
SIGNAL_EXPIRATION_DAYS = {
    "SIG-01": 45,
    "SIG-02": 60,
    "SIG-03": 90,
    "SIG-04": 180,
    "SIG-06": 45,
    "SIG-07": 60,
    "SIG-08": 180,
}

CATEGORY_FIT = {
    "Medical/Dental": 15,
    "Childcare": 15,
    "Office": 10,
    "Coworking": 10,
    "Retail": 8,
    "Fitness": 8,
    "Hospitality": 8,
    "Warehouse/Industrial": 5,
    "Other": 5,
}

# See module docstring for why these specific fields, not the full §14 Required=Yes list.
COMPLETENESS_FIELDS = ["Phone", "Website", "Email", "ZIP", "Contact_Name", "Company"]

CATEGORY_THRESHOLDS = [
    (80, "Hot"),
    (60, "Warm"),
    (40, "Nurture"),
    (0, "Low Priority"),
]


def compute_recency_score(signal_id: str, signal_date_str: str | None, today: date | None = None) -> float:
    """20 x (1 - days_since_signal / expiration_days), floored at 0 (§20)."""
    today = today or date.today()
    if not signal_date_str:
        return 0.0
    try:
        signal_date = date.fromisoformat(signal_date_str)
    except ValueError:
        return 0.0
    expiration_days = SIGNAL_EXPIRATION_DAYS.get(signal_id, 90)
    days_since = (today - signal_date).days
    raw = 20 * (1 - days_since / expiration_days)
    return max(0.0, raw)


def compute_completeness_score(lead: dict[str, Any]) -> float:
    populated = sum(1 for field in COMPLETENESS_FIELDS if lead.get(field))
    return 10 * populated / len(COMPLETENESS_FIELDS)


def compute_value_modifier(lead: dict[str, Any]) -> int:
    return 5 if lead.get("Signal_ID") == "SIG-07" else 0


def category_from_score(score: int) -> str:
    for threshold, category in CATEGORY_THRESHOLDS:
        if score >= threshold:
            return category
    return "Low Priority"


def score_lead(lead: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    """Returns {Lead_Score, Score_Breakdown, Lead_Category} for one lead.

    Each feature is rounded to a whole number before summing -- this is what makes
    §20's worked example (91.4 in raw arithmetic) land on exactly 91, and it keeps
    Score_Breakdown's individual numbers human-readable (NFR-011 explainability).
    """
    signal_id = lead.get("Signal_ID")

    signal_strength = SIGNAL_STRENGTH.get(signal_id, 0)
    recency = round(compute_recency_score(signal_id, lead.get("Signal_Date"), today))
    category_fit = CATEGORY_FIT.get(lead.get("Property_Type"), 5)
    completeness = round(compute_completeness_score(lead))
    ai_confidence = round(10 * (lead.get("AI_Confidence") or 0))
    value_modifier = compute_value_modifier(lead)

    total = min(100, signal_strength + recency + category_fit + completeness + ai_confidence + value_modifier)

    breakdown = {
        "signal_strength": signal_strength,
        "recency": recency,
        "category_fit": category_fit,
        "completeness": completeness,
        "ai_confidence": ai_confidence,
        "value_modifier": value_modifier,
        "total": total,
    }

    return {
        "Lead_Score": total,
        "Score_Breakdown": json.dumps(breakdown),
        "Lead_Category": category_from_score(total),
    }


def score_batch(leads: list[dict[str, Any]], today: date | None = None) -> list[dict[str, Any]]:
    scored = []
    for lead in leads:
        result = score_lead(lead, today)
        updated = dict(lead)
        updated.update(result)
        scored.append(updated)
    return scored
