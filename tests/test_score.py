import json
from datetime import date

import score


def test_category_from_score_boundaries():
    # AC-007.2: exact threshold boundaries (39/40, 59/60, 79/80)
    assert score.category_from_score(39) == "Low Priority"
    assert score.category_from_score(40) == "Nurture"
    assert score.category_from_score(59) == "Nurture"
    assert score.category_from_score(60) == "Warm"
    assert score.category_from_score(79) == "Warm"
    assert score.category_from_score(80) == "Hot"
    assert score.category_from_score(100) == "Hot"
    assert score.category_from_score(0) == "Low Priority"


def test_compute_recency_score_fresh_signal_scores_near_max():
    today = date(2026, 9, 10)
    # Signal dated today -> 0 days elapsed -> full 20 points
    assert score.compute_recency_score("SIG-01", "2026-09-10", today) == 20.0


def test_compute_recency_score_fully_expired_floors_at_zero():
    today = date(2026, 9, 10)
    # SIG-01 expires after 45 days; 100 days elapsed is well past that
    old_date = "2026-06-01"
    assert score.compute_recency_score("SIG-01", old_date, today) == 0.0


def test_compute_recency_score_missing_date_returns_zero():
    assert score.compute_recency_score("SIG-01", None) == 0.0


def test_compute_recency_score_invalid_date_returns_zero():
    assert score.compute_recency_score("SIG-01", "not-a-date") == 0.0


def test_compute_completeness_score_all_fields_present():
    lead = {f: "x" for f in score.COMPLETENESS_FIELDS}
    assert score.compute_completeness_score(lead) == 10.0


def test_compute_completeness_score_no_fields_present():
    assert score.compute_completeness_score({}) == 0.0


def test_compute_completeness_score_partial():
    lead = {"Phone": "x", "Website": "x", "Email": None}
    # 2 of 6 fields populated
    assert score.compute_completeness_score(lead) == 10 * 2 / 6


def test_compute_value_modifier_sig07_present():
    assert score.compute_value_modifier({"Signal_ID": "SIG-07"}) == 5


def test_compute_value_modifier_other_signal():
    assert score.compute_value_modifier({"Signal_ID": "SIG-03"}) == 0


def test_score_lead_reproduces_prd_worked_example(mocker):
    # §20 worked example: SIG-01, 4 days old (45-day expiration), Medical/Dental,
    # 90% complete fields, AI_Confidence 0.94, no SIG-07 modifier -> 91 -> Hot.
    mocker.patch.object(score, "compute_completeness_score", return_value=9.0)

    lead = {
        "Signal_ID": "SIG-01",
        "Signal_Date": "2026-09-06",  # 4 days before the fixed "today" below
        "Property_Type": "Medical/Dental",
        "AI_Confidence": 0.94,
    }

    result = score.score_lead(lead, today=date(2026, 9, 10))

    assert result["Lead_Score"] == 91
    assert result["Lead_Category"] == "Hot"

    breakdown = json.loads(result["Score_Breakdown"])
    assert breakdown == {
        "signal_strength": 40,
        "recency": 18,
        "category_fit": 15,
        "completeness": 9,
        "ai_confidence": 9,
        "value_modifier": 0,
        "total": 91,
    }


def test_score_lead_caps_total_at_100(mocker):
    mocker.patch.dict(score.SIGNAL_STRENGTH, {"SIG-01": 200})
    lead = {
        "Signal_ID": "SIG-01",
        "Signal_Date": "2026-09-10",
        "Property_Type": "Medical/Dental",
        "AI_Confidence": 1.0,
    }

    result = score.score_lead(lead, today=date(2026, 9, 10))

    assert result["Lead_Score"] == 100
    assert result["Lead_Category"] == "Hot"


def test_score_lead_unknown_signal_and_category_use_safe_defaults():
    lead = {"Signal_ID": "SIG-UNKNOWN", "Property_Type": "Nonexistent", "Signal_Date": None}

    result = score.score_lead(lead, today=date(2026, 9, 10))

    breakdown = json.loads(result["Score_Breakdown"])
    assert breakdown["signal_strength"] == 0
    assert breakdown["category_fit"] == 5  # falls back to the "Other"-tier weight
    assert result["Lead_Category"] == "Low Priority"


def test_score_batch_preserves_lead_fields_and_adds_score_fields():
    leads = [
        {"Lead_ID": "L-000001", "Signal_ID": "SIG-03", "Signal_Date": "2026-09-10", "Property_Type": "Coworking"},
        {"Lead_ID": "L-000002", "Signal_ID": "SIG-03", "Signal_Date": "2026-09-10", "Property_Type": "Retail"},
    ]

    scored = score.score_batch(leads, today=date(2026, 9, 10))

    assert len(scored) == 2
    assert scored[0]["Lead_ID"] == "L-000001"
    assert "Lead_Score" in scored[0]
    assert "Score_Breakdown" in scored[0]
    assert "Lead_Category" in scored[0]
