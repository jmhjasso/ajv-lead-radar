import json
from datetime import datetime, timezone
from pathlib import Path

import normalize

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "raw_src01_sample.json"
FIXED_NOW = datetime(2026, 9, 10, 15, 0, 0, tzinfo=timezone.utc)


def load_fixture_records():
    return json.loads(FIXTURE_PATH.read_text())


def test_load_mapping_src01():
    mapping = normalize.load_mapping("SRC-01")
    assert mapping["source_id"] == "SRC-01"
    assert mapping["fixed_fields"]["Lead_Source"] == "SRC-01"


def test_parse_street_address():
    assert normalize.parse_street_address("123 SE 5th St, Bentonville, AR 72712, USA") == "123 SE 5th St"


def test_parse_street_address_handles_none():
    assert normalize.parse_street_address(None) == ""


def test_parse_zip_extracts_five_digits():
    assert normalize.parse_zip("123 SE 5th St, Bentonville, AR 72712, USA") == "72712"


def test_parse_zip_missing_returns_empty():
    assert normalize.parse_zip(None) == ""
    assert normalize.parse_zip("no zip here") == ""


def test_normalize_record_maps_complete_record():
    raw = load_fixture_records()[0]
    mapping = normalize.load_mapping("SRC-01")

    lead = normalize.normalize_record(raw, mapping, now=FIXED_NOW)

    assert lead["Lead_Name"] == "Ozark Family Dental"
    assert lead["Address"] == "123 SE 5th St"
    assert lead["City"] == "Bentonville"
    assert lead["State"] == "AR"
    assert lead["ZIP"] == "72712"
    assert lead["Phone"] == "+14795551234"
    assert lead["Website"] == "https://ozarkfamilydental.com"
    assert lead["Property_Type"] == "Medical/Dental"
    assert lead["Lead_Source"] == "SRC-01"
    assert lead["Source_URL"] == "https://maps.google.com/?cid=1111111111"
    assert lead["Signal_ID"] == "SIG-03"
    assert lead["Recommended_Service"] == "Recurring Janitorial"
    assert lead["Status"] == "New"
    assert lead["Discovered_Date"] == "2026-09-10"
    assert lead["Signal_Date"] == lead["Discovered_Date"]
    assert "0 review(s)" in lead["Source_Evidence"]


def test_normalize_record_ai_placeholders():
    raw = load_fixture_records()[0]
    mapping = normalize.load_mapping("SRC-01")

    lead = normalize.normalize_record(raw, mapping, now=FIXED_NOW)

    assert lead["AI_Confidence"] == 0
    assert lead["AI_Model_Used"] == "none (deterministic-only pilot)"
    assert lead["Prompt_Version"] == "n/a"
    # Not yet computed -- score.py's job (Step 6)
    assert lead["Lead_Score"] is None
    assert lead["Score_Breakdown"] is None
    assert lead["Lead_Category"] is None


def test_normalize_record_missing_name_is_incomplete():
    raw = load_fixture_records()[1]
    mapping = normalize.load_mapping("SRC-01")

    lead = normalize.normalize_record(raw, mapping, now=FIXED_NOW)

    assert lead["Status"] == "Incomplete"
    assert "Lead_Name" in lead["_missing_fields"]


def test_normalize_record_missing_address_is_incomplete():
    raw = load_fixture_records()[2]
    mapping = normalize.load_mapping("SRC-01")

    lead = normalize.normalize_record(raw, mapping, now=FIXED_NOW)

    assert lead["Status"] == "Incomplete"
    assert "Address" in lead["_missing_fields"]


def test_normalize_batch_returns_one_lead_per_raw_record():
    raw_records = load_fixture_records()

    leads = normalize.normalize_batch(raw_records, source_id="SRC-01")

    assert len(leads) == len(raw_records)
    assert [l["Status"] for l in leads] == ["New", "Incomplete", "Incomplete"]
