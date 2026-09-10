import json
from datetime import date
from pathlib import Path

import pipeline

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "raw_src01_sample.json"


def load_fixture_records():
    return json.loads(FIXTURE_PATH.read_text())


def make_raw(name, address, city, property_type="Medical/Dental", user_rating_count=0):
    return {
        "source_id": "SRC-01",
        "place_id": f"place-{name}",
        "name": name,
        "formatted_address": address,
        "city_query": city,
        "property_type": property_type,
        "category_query": "test query",
        "types": [],
        "primary_type": None,
        "rating": None,
        "user_rating_count": user_rating_count,
        "phone": "+14795551234",
        "website": "https://example.com",
        "source_url": "https://maps.google.com/?cid=999",
        "retrieved_at": "2026-09-10T14:00:00+00:00",
    }


def test_generate_evidence_id_starts_at_one_when_empty():
    assert pipeline.generate_evidence_id([]) == "E-000001"


def test_generate_evidence_id_increments():
    existing = [{"Evidence_ID": "E-000004"}, {"Evidence_ID": "E-000002"}]
    assert pipeline.generate_evidence_id(existing) == "E-000005"


def test_run_pipeline_core_complete_lead_gets_scored_and_ready_for_review():
    raw = [make_raw("Ozark Family Dental", "123 SE 5th St, Bentonville, AR 72712, USA", "Bentonville")]

    result = pipeline.run_pipeline_core(raw, existing_leads=[], today=date(2026, 9, 10))

    assert len(result["new_leads"]) == 1
    lead = result["new_leads"][0]
    assert lead["Status"] == "Ready_For_Review"
    assert lead["Lead_Score"] is not None
    assert lead["Lead_Category"] is not None
    assert lead["Lead_ID"] == "L-000001"
    assert result["evidence_appends"] == []
    assert result["possible_duplicates"] == []


def test_run_pipeline_core_incomplete_lead_not_scored():
    raw = load_fixture_records()  # index 1 has no name -> Incomplete

    result = pipeline.run_pipeline_core(raw, existing_leads=[], today=date(2026, 9, 10))

    incomplete_leads = [l for l in result["new_leads"] if l["Status"] == "Incomplete"]
    assert len(incomplete_leads) == 2  # fixture has two malformed records (missing name, missing address)
    for lead in incomplete_leads:
        assert lead["Lead_Score"] is None
        assert lead["Score_Breakdown"] is None


def test_run_pipeline_core_exact_duplicate_produces_evidence_not_new_lead():
    existing_leads = [
        {"Lead_ID": "L-000001", "Lead_Name": "Ozark Family Dental", "Address": "123 SE 5th St", "City": "Bentonville"}
    ]
    raw = [make_raw("ozark family dental", "123 SE 5th St, Bentonville, AR 72712, USA", "Bentonville")]

    result = pipeline.run_pipeline_core(raw, existing_leads=existing_leads, today=date(2026, 9, 10))

    assert result["new_leads"] == []
    assert result["possible_duplicates"] == []
    assert len(result["evidence_appends"]) == 1
    evidence = result["evidence_appends"][0]
    assert evidence["Lead_ID"] == "L-000001"
    assert evidence["Source_ID"] == "SRC-01"
    assert evidence["Evidence_ID"] == "E-000001"


def test_run_pipeline_core_possible_duplicate_not_written_anywhere():
    existing_leads = [
        {"Lead_ID": "L-000001", "Lead_Name": "Ozark Family Dental", "Address": "123 SE 5th St", "City": "Bentonville"}
    ]
    # Same name, address differs by a suite number -- lands in the fuzzy flag band
    raw = [make_raw("Ozark Family Dental", "123 SE 5th St Suite 2, Bentonville, AR 72712, USA", "Bentonville")]

    result = pipeline.run_pipeline_core(raw, existing_leads=existing_leads, today=date(2026, 9, 10))

    assert result["new_leads"] == []
    assert result["evidence_appends"] == []
    assert len(result["possible_duplicates"]) == 1
    assert result["possible_duplicates"][0]["matched_lead_id"] == "L-000001"


def test_run_pipeline_core_evidence_ids_increment_within_one_batch():
    existing_leads = [
        {"Lead_ID": "L-000001", "Lead_Name": "Business A", "Address": "1 Main St", "City": "Rogers"},
        {"Lead_ID": "L-000002", "Lead_Name": "Business B", "Address": "2 Main St", "City": "Rogers"},
    ]
    raw = [
        make_raw("business a", "1 Main St, Rogers, AR 72756, USA", "Rogers"),
        make_raw("business b", "2 Main St, Rogers, AR 72756, USA", "Rogers"),
    ]

    result = pipeline.run_pipeline_core(raw, existing_leads=existing_leads, today=date(2026, 9, 10))

    assert [e["Evidence_ID"] for e in result["evidence_appends"]] == ["E-000001", "E-000002"]
