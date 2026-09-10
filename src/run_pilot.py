"""Manual/on-demand full pipeline run (PRD §62 Step 10, §46a "operator clicks run").

Usage:
    python src/run_pilot.py                 # full run: 8 cities x 8 categories
    python src/run_pilot.py --cities Bentonville Rogers --categories Coworking

This is the Pilot Slice's entire operator-facing entrypoint: collect -> normalize ->
dedup -> score -> write to Sheets. No scheduling, no alerting -- those are explicitly
out of scope until the ~Dec 4 full MVP continuation (§46a).
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

import collector_src01
import pipeline
import sheets_io


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the AJV Lead Radar Pilot Slice pipeline.")
    parser.add_argument("--cities", nargs="+", default=None, help="Subset of the 8 priority cities (default: all)")
    parser.add_argument(
        "--categories", nargs="+", default=None,
        help="Subset of category keys, e.g. Coworking Medical/Dental (default: all)",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()

    config = sheets_io.get_env_config()

    cities = args.cities or collector_src01.CITIES
    if args.categories:
        category_queries = {k: v for k, v in collector_src01.CATEGORY_QUERIES.items() if k in args.categories}
    else:
        category_queries = collector_src01.CATEGORY_QUERIES

    print(f"Collecting from SRC-01 for {len(cities)} cities x {len(category_queries)} categories...")
    raw_records = collector_src01.collect(config["GOOGLE_PLACES_API_KEY"], cities=cities, category_queries=category_queries)
    print(f"  {len(raw_records)} raw candidate records.")

    client = sheets_io.get_client(config["GOOGLE_SHEETS_CREDENTIALS_JSON"], "config/authorized_user.json")
    spreadsheet = sheets_io.get_spreadsheet(client, config["GOOGLE_SHEETS_SPREADSHEET_ID"])

    existing_leads = sheets_io.read_leads(spreadsheet)
    existing_evidence = sheets_io.read_evidence(spreadsheet)
    print(f"  {len(existing_leads)} leads already in the Sheet.")

    result = pipeline.run_pipeline_core(raw_records, existing_leads, existing_evidence)

    sheets_io.append_leads(spreadsheet, result["new_leads"])
    sheets_io.append_evidence(spreadsheet, result["evidence_appends"])
    sheets_io.touch_source_config(spreadsheet, "SRC-01", datetime.now(timezone.utc))

    ready = [l for l in result["new_leads"] if l["Status"] == "Ready_For_Review"]
    incomplete = [l for l in result["new_leads"] if l["Status"] == "Incomplete"]

    print(f"\nWrote {len(result['new_leads'])} new leads ({len(ready)} Ready_For_Review, {len(incomplete)} Incomplete).")
    print(f"Appended {len(result['evidence_appends'])} evidence entries to existing leads (exact duplicates).")

    if result["possible_duplicates"]:
        os.makedirs("data", exist_ok=True)
        out_path = f"data/possible_duplicates_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result["possible_duplicates"], f, indent=2)
        print(
            f"{len(result['possible_duplicates'])} possible duplicates held for manual review "
            f"(not written to the Sheet, per AC-004.2) -> {out_path}"
        )

    if ready:
        top = sorted(ready, key=lambda l: l["Lead_Score"], reverse=True)[:5]
        print("\nTop scored leads this run:")
        for lead in top:
            print(f"  {lead['Lead_Score']:3d} {lead['Lead_Category']:12s} {lead['Lead_Name']} ({lead['City']})")


if __name__ == "__main__":
    main()
