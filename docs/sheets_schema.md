# Google Sheets Datastore Schema (PRD §14)

One spreadsheet, four tabs. This is the literal column list from PRD §14/§14a — nothing
added, nothing renamed. Column order matches the order below (left to right).

## Tab 1: `Lead`

One row per real-world commercial business/opportunity.

| Column | Type | Required | Validation | Example |
|---|---|---|---|---|
| Lead_ID | text | Yes | Unique, immutable, format `L-000001` | `L-000042` |
| Discovered_Date | date | Yes | ISO 8601 (`YYYY-MM-DD`) | `2026-09-09` |
| Signal_ID | text | Yes | One of SIG-01..SIG-08 (§13) | `SIG-03` |
| Signal_Date | date | Yes | ISO 8601, ≤ Discovered_Date | `2026-09-05` |
| Lead_Name | text | Yes | Non-empty | `Ozark Family Dental` |
| Company | text | No | — | `Ozark Family Dental PLLC` |
| Contact_Name | text | No | — | `Dr. J. Smith` |
| Address | text | Yes | Must geocode to one of the 8 priority cities | `123 SE 5th St` |
| City | text (dropdown) | Yes | One of: Bentonville, Rogers, Centerton, Bella Vista, Springdale, Fayetteville, Lowell, Cave Springs | `Bentonville` |
| State | text | Yes | Fixed `AR` | `AR` |
| ZIP | text | No | 5-digit | `72712` |
| Phone | text | No | E.164-normalizable | `+14795551234` |
| Email | text | No | RFC 5322 format | — |
| Website | text (URL) | No | Valid URL | `https://ozarkfamilydental.com` |
| Property_Type | text (dropdown) | Yes | Office, Medical/Dental, Retail, Coworking, Childcare, Fitness, Hospitality, Warehouse/Industrial, Other | `Medical/Dental` |
| Business_Type | text | No | Free text / Places category | `Dental clinic` |
| Lead_Source | text | Yes | Source_ID from §12 (Pilot: `SRC-01` only) | `SRC-01` |
| Source_URL | text (URL) | Yes | Valid URL or portal reference | — |
| Source_Evidence | text | Yes | Non-empty, append-only across duplicate merges | `"New Places listing, 0 reviews, observed 2026-09-09"` |
| Recommended_Service | text (dropdown) | Yes | Post-Construction Clean, Move-In Clean, Recurring Janitorial, One-Time Deep Clean | `Recurring Janitorial` |
| Lead_Score | number | Yes | Integer 0-100 | `87` |
| Score_Breakdown | text (JSON) | Yes | Lists each contributing feature + point value (§20) | `{"signal_strength":20,...}` |
| Lead_Category | text (dropdown) | Yes | Hot, Warm, Nurture, Low Priority (derived from score, §20) | `Hot` |
| AI_Confidence | number | Yes | 0-1 float; **Pilot Slice: fixed 0 (no AI classification yet, §46a)** | `0` |
| AI_Model_Used | text | Yes | **Pilot Slice: `"none (deterministic-only pilot)"`** | — |
| Prompt_Version | text | Yes | **Pilot Slice: `"n/a"`** | — |
| Status | text (dropdown) | Yes | New, Enriched, Scored, Ready_For_Review, Approved, Rejected, Needs_Enrichment, Incomplete, Contacted, Responded, Quoted, Won, Lost, Stale (§14a) | `Ready_For_Review` |
| Last_Contacted | date | No | ISO 8601 | — |
| Next_Action | text | No | — | — |
| Estimated_Value | number | No | ≥ 0, USD/month | `350` |
| Notes | text | No | — | — |
| Rejection_Reason | text (dropdown) | Conditional (required if Status=Rejected) | Bad Data, Wrong Category, Too Small, Already Customer, Not Interested, Other | — |
| Created_At | datetime | Yes | System, ISO 8601 | `2026-09-09T14:02:11Z` |
| Updated_At | datetime | Yes | System, auto-updated on every write | `2026-09-09T14:10:00Z` |

## Tab 2: `Source_Config`

One row per source (Pilot Slice: one row, `SRC-01`).

| Column | Type | Notes |
|---|---|---|
| Source_ID | text | `SRC-01`, `SRC-02`, `SRC-03` (only SRC-01 active in Pilot Slice) |
| Enabled | boolean (TRUE/FALSE) | Lets the collector be turned off without redeploying (FR-018) |
| Last_Run_At | datetime | Updated by the collector each run |
| Last_Success_At | datetime | Updated on success only |
| Error_Count_7d | number | Rolling error count |
| Rate_Limit_Notes | text | Free-text notes on quota/rate limits observed |

## Tab 3: `Evidence_Log`

One row per raw signal merged into a Lead — append-only, never overwritten.

| Column | Type | Notes |
|---|---|---|
| Evidence_ID | text | Unique ID |
| Lead_ID | text | Foreign key to `Lead` tab |
| Source_ID | text | e.g. `SRC-01` |
| Source_URL | text (URL) | Where this evidence came from |
| Retrieved_At | datetime | ISO 8601 |
| Raw_Snippet | text | Short raw excerpt supporting the signal |

## Tab 4: `Status_History`

One row per status change — the audit trail (NFR-010).

| Column | Type | Notes |
|---|---|---|
| History_ID | text | Unique ID |
| Lead_ID | text | Foreign key to `Lead` tab |
| From_Status | text | Prior status |
| To_Status | text | New status |
| Changed_By | text | `system` or a person's name |
| Changed_At | datetime | ISO 8601 |
| Note | text | Optional free text |

## Pilot Slice notes (deviations are additive-only, not schema changes)

- Every column above stays exactly as specified — the Pilot Slice does not simplify the
  schema (PRD §46a: "nothing in §14 changes... SRC-02/03 and AI classification plug into
  the same schema and pipeline later without rework").
- `AI_Confidence`, `AI_Model_Used`, `Prompt_Version` are still required fields, just filled
  with fixed placeholder values during the pilot since AI classification is out of scope
  until the stretch goal or Phase 2.
- `Score_Breakdown`'s AI-confidence sub-score (§20) uses `AI_Confidence = 0` for every lead
  during the pilot, which is mathematically consistent — it just means that 10-point
  component of every score is 0 until AI classification is added.

## How to set this up

**Option A — you create it (fastest):** open Google Sheets, create a new spreadsheet named
`AJV Lead Radar`, add the 4 tabs above with these exact column headers in row 1, share it
with edit access to whichever Google account will run the API calls (can be the same
account), and send me the spreadsheet ID (the long string in the URL between `/d/` and
`/edit`).

**Option B — I provision it via the Sheets API:** once you've created a Google Cloud service
account and shared a blank spreadsheet with its email (I'll give you those exact steps), I
can write a one-time setup script that creates all 4 tabs and headers programmatically — useful
if we end up re-creating this (e.g., a test spreadsheet vs. the real one).

Either is fine for the Pilot Slice. Given time constraints, Option A is faster to start with.
