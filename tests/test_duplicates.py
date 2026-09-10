import deduplicate as dedup


def make_lead(lead_id, name, address, city="Bentonville"):
    return {"Lead_ID": lead_id, "Lead_Name": name, "Address": address, "City": city}


def test_normalize_key_strips_punctuation_and_case():
    assert dedup.normalize_key("Ozark Family Dental, PLLC!") == "ozark family dental pllc"


def test_normalize_key_handles_none():
    assert dedup.normalize_key(None) == ""


def test_compute_dedup_hash_is_consistent_for_same_input():
    lead_a = make_lead(None, "Ozark Family Dental", "123 SE 5th St")
    lead_b = make_lead(None, "ozark family dental", "123 SE 5th ST")
    assert dedup.compute_dedup_hash(lead_a) == dedup.compute_dedup_hash(lead_b)


def test_compute_dedup_hash_differs_for_different_business():
    lead_a = make_lead(None, "Ozark Family Dental", "123 SE 5th St")
    lead_b = make_lead(None, "Vault 90", "456 N Walton Blvd")
    assert dedup.compute_dedup_hash(lead_a) != dedup.compute_dedup_hash(lead_b)


def test_generate_lead_id_starts_at_one_when_empty():
    assert dedup.generate_lead_id([]) == "L-000001"


def test_generate_lead_id_increments_from_max_existing():
    existing = [make_lead("L-000003", "A", "1 St"), make_lead("L-000007", "B", "2 St")]
    assert dedup.generate_lead_id(existing) == "L-000008"


def test_dedup_batch_exact_match_merges_no_new_lead_id():
    # AC-004.1
    existing = [make_lead("L-000001", "Ozark Family Dental", "123 SE 5th St")]
    candidate = make_lead(None, "ozark family dental", "123 se 5th st")  # same business, casing differs

    result = dedup.dedup_batch([candidate], existing)

    assert result["new"] == []
    assert result["possible_duplicates"] == []
    assert len(result["exact_duplicates"]) == 1
    matched_candidate, matched_existing = result["exact_duplicates"][0]
    assert matched_existing["Lead_ID"] == "L-000001"


def test_dedup_batch_fuzzy_match_flagged_not_merged_or_created():
    # AC-004.2: 75-89% band -> flagged, not merged, not auto-created
    existing = [make_lead("L-000001", "Ozark Family Dental", "123 SE 5th St")]
    # Same business name, address differs only by a suite number -- ~89% similarity
    candidate = make_lead(None, "Ozark Family Dental", "123 SE 5th St Suite 2")

    result = dedup.dedup_batch([candidate], existing)

    assert result["new"] == []
    assert result["exact_duplicates"] == []
    assert len(result["possible_duplicates"]) == 1
    matched_candidate, matched_existing, score = result["possible_duplicates"][0]
    assert matched_existing["Lead_ID"] == "L-000001"
    assert dedup.FUZZY_LOW <= score < 100


def test_dedup_batch_distinct_business_gets_new_lead_id():
    existing = [make_lead("L-000001", "Ozark Family Dental", "123 SE 5th St")]
    candidate = make_lead(None, "Vault 90 Coworking", "789 Completely Different Ave")

    result = dedup.dedup_batch([candidate], existing)

    assert result["exact_duplicates"] == []
    assert result["possible_duplicates"] == []
    assert len(result["new"]) == 1
    assert result["new"][0]["Lead_ID"] == "L-000002"


def test_dedup_batch_catches_duplicate_within_same_batch():
    # Two raw records for the same real business surfaced by two different category
    # searches in one collection run (e.g. "office" and "coworking" both matching it).
    existing: list[dict] = []
    candidate_a = make_lead(None, "iPropel Center", "100 SW A St")
    candidate_b = make_lead(None, "ipropel center", "100 sw a st")

    result = dedup.dedup_batch([candidate_a, candidate_b], existing)

    assert len(result["new"]) == 1
    assert len(result["exact_duplicates"]) == 1
    assert result["new"][0]["Lead_ID"] == "L-000001"


def test_dedup_batch_empty_candidates_returns_empty_buckets():
    result = dedup.dedup_batch([], [make_lead("L-000001", "A", "1 St")])
    assert result == {"new": [], "exact_duplicates": [], "possible_duplicates": []}
