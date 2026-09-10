import json
from pathlib import Path

import collector_src01 as collector

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "places_text_search_response.json"


def load_fixture_places():
    return json.loads(FIXTURE_PATH.read_text())["places"]


def test_is_in_target_city_matches():
    assert collector.is_in_target_city("123 SE 5th St, Bentonville, AR 72712, USA", "Bentonville")


def test_is_in_target_city_rejects_other_city():
    assert not collector.is_in_target_city("789 Main St, Siloam Springs, AR 72761, USA", "Bentonville")


def test_is_in_target_city_handles_empty_address():
    assert not collector.is_in_target_city("", "Bentonville")


def test_passes_new_listing_heuristic_zero_reviews():
    place = {"userRatingCount": 0}
    assert collector.passes_new_listing_heuristic(place)


def test_passes_new_listing_heuristic_at_threshold():
    place = {"userRatingCount": collector.NEW_LISTING_MAX_REVIEWS}
    assert collector.passes_new_listing_heuristic(place)


def test_passes_new_listing_heuristic_rejects_established_business():
    place = {"userRatingCount": 218}
    assert not collector.passes_new_listing_heuristic(place)


def test_passes_new_listing_heuristic_missing_count_treated_as_zero():
    assert collector.passes_new_listing_heuristic({})


def test_to_raw_record_shape():
    place = load_fixture_places()[0]
    record = collector.to_raw_record(place, "Bentonville", "Medical/Dental", "medical or dental office in Bentonville, AR")

    assert record["source_id"] == "SRC-01"
    assert record["place_id"] == "ChIJ_new_dental_bentonville"
    assert record["name"] == "Ozark Family Dental"
    assert record["city_query"] == "Bentonville"
    assert record["property_type"] == "Medical/Dental"
    assert record["user_rating_count"] == 0
    assert record["source_url"] == "https://maps.google.com/?cid=1111111111"
    assert "retrieved_at" in record


def test_collect_filters_out_of_city_and_established_businesses(mocker):
    fixture_places = load_fixture_places()
    mocker.patch.object(collector, "search_places_text", return_value=fixture_places)

    records = collector.collect(
        api_key="test-key",
        cities=["Bentonville"],
        category_queries={"Medical/Dental": "medical or dental office"},
    )

    # 3 raw places in the fixture: one new listing in-scope, one established (high review
    # count) in-scope, one out-of-city. Only the new listing should survive both filters.
    assert len(records) == 1
    assert records[0]["place_id"] == "ChIJ_new_dental_bentonville"


def test_collect_returns_empty_on_search_failure(mocker):
    mocker.patch.object(collector, "search_places_text", return_value=[])

    records = collector.collect(
        api_key="test-key",
        cities=["Bentonville"],
        category_queries={"Medical/Dental": "medical or dental office"},
    )

    assert records == []


def test_search_places_text_returns_empty_list_on_request_exception(mocker):
    mocker.patch.object(collector.requests, "post", side_effect=collector.requests.RequestException("boom"))

    result = collector.search_places_text("query", "fake-key")

    assert result == []
