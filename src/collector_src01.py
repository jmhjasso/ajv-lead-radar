"""SRC-01 collector: Google Places API (New), Text Search.

PRD refs: §12 SRC-01, §16 Lead Collector, §10 FR-001/FR-002, §13 SIG-03, §62 Step 4.

Queries the 8 priority NWA cities against a fixed set of commercial-category search
phrases, keeps only results inside a target city, and applies the SIG-03 "new listing"
heuristic (near-zero review count) — this is the only signal SRC-01 can support on its
own, and it's what keeps this collector from just dumping every existing business in NWA
into the pipeline (that's SIG-08, explicitly out of scope for the Pilot Slice, PRD §46a).

Emits raw records (not yet the canonical Lead schema — that mapping is normalize.py's job).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

import requests
from dotenv import load_dotenv

PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.types",
        "places.primaryType",
        "places.rating",
        "places.userRatingCount",
        "places.internationalPhoneNumber",
        "places.websiteUri",
        "places.googleMapsUri",
    ]
)

# PRD §1 Document Control — the 8 priority NWA cities.
CITIES = [
    "Bentonville",
    "Rogers",
    "Centerton",
    "Bella Vista",
    "Springdale",
    "Fayetteville",
    "Lowell",
    "Cave Springs",
]

# PRD §10 FR-002 commercial categories mapped to §14 Property_Type enum values, each
# with one representative search phrase. One phrase/category keeps the per-run call count
# to CITIES x CATEGORIES = 64 for the Pilot Slice, in line with the "quality over
# quantity" principle (PRD §3/§45) and the <$10/month cost target (NFR-001).
CATEGORY_QUERIES: dict[str, str] = {
    "Office": "office space",
    "Medical/Dental": "medical or dental office",
    "Retail": "retail store",
    "Coworking": "coworking space",
    "Childcare": "childcare center",
    "Fitness": "fitness center",
    "Hospitality": "hotel",
    "Warehouse/Industrial": "warehouse",
}

# SIG-03 heuristic (§13): "near-zero reviews" — Assumption: <=3 reviews is treated as a
# likely-new listing. Tunable; not validated against real NWA data yet (flag for Step 8 QA).
NEW_LISTING_MAX_REVIEWS = 3


def search_places_text(
    query: str, api_key: str, region_code: str = "US"
) -> list[dict[str, Any]]:
    """Calls the Places API (New) Text Search endpoint. Returns [] on any request failure
    rather than raising, so one bad query doesn't take down the whole collection run
    (PRD NFR-003: isolated failure domains)."""
    try:
        response = requests.post(
            PLACES_TEXT_SEARCH_URL,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": FIELD_MASK,
            },
            json={"textQuery": query, "regionCode": region_code},
            timeout=15,
        )
        response.raise_for_status()
        return response.json().get("places", [])
    except requests.RequestException as exc:
        print(f"[collector_src01] request failed for query '{query}': {exc}", file=sys.stderr)
        return []


def is_in_target_city(formatted_address: str, city: str) -> bool:
    """Case-insensitive substring check — Places' own address string is the only
    location signal used here, no geocoding round-trip needed for the Pilot Slice."""
    if not formatted_address:
        return False
    return city.lower() in formatted_address.lower()


def passes_new_listing_heuristic(place: dict[str, Any], max_reviews: int = NEW_LISTING_MAX_REVIEWS) -> bool:
    """SIG-03: a listing with no/near-zero reviews is the pilot's only usable signal
    from this source. Missing userRatingCount is treated as 0 (passes)."""
    return place.get("userRatingCount", 0) <= max_reviews


def to_raw_record(place: dict[str, Any], city: str, property_type: str, query: str) -> dict[str, Any]:
    """Shapes one Places result into a raw record for normalize.py. Field names here are
    intentionally NOT the canonical Lead schema (§14) — that mapping happens in
    normalize.py via config/mappings/src01.json, keeping the collector source-agnostic
    about the target schema."""
    return {
        "source_id": "SRC-01",
        "place_id": place.get("id"),
        "name": place.get("displayName", {}).get("text"),
        "formatted_address": place.get("formattedAddress"),
        "city_query": city,
        "property_type": property_type,
        "category_query": query,
        "types": place.get("types", []),
        "primary_type": place.get("primaryType"),
        "rating": place.get("rating"),
        "user_rating_count": place.get("userRatingCount", 0),
        "phone": place.get("internationalPhoneNumber"),
        "website": place.get("websiteUri"),
        "source_url": place.get("googleMapsUri"),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


def collect(
    api_key: str,
    cities: list[str] | None = None,
    category_queries: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Runs every (city, category) query, filters to target cities + the SIG-03
    new-listing heuristic, and returns the raw record list. This is FR-001/FR-002's
    'discover + filter before normalization' step (AC-001.1/AC-001.2)."""
    cities = cities if cities is not None else CITIES
    category_queries = category_queries if category_queries is not None else CATEGORY_QUERIES

    records: list[dict[str, Any]] = []
    for property_type, phrase in category_queries.items():
        for city in cities:
            query = f"{phrase} in {city}, AR"
            for place in search_places_text(query, api_key):
                address = place.get("formattedAddress", "")
                if not is_in_target_city(address, city):
                    continue  # AC-001.2: exclude records outside the 8 priority cities
                if not passes_new_listing_heuristic(place):
                    continue  # SIG-08 territory (existing business, no fresh signal) — out of pilot scope
                records.append(to_raw_record(place, city, property_type, query))
    return records


def main() -> None:
    load_dotenv()
    api_key = os.environ.get("GOOGLE_PLACES_API_KEY")
    if not api_key:
        sys.exit("GOOGLE_PLACES_API_KEY is not set in .env")

    records = collect(api_key)
    print(f"Collected {len(records)} candidate SIG-03 records across {len(CITIES)} cities.")

    os.makedirs("data", exist_ok=True)
    out_path = f"data/raw_src01_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"Wrote raw records to {out_path} (local only — gitignored, never committed).")


if __name__ == "__main__":
    main()
