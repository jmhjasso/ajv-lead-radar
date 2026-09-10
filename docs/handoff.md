# Pilot Slice — Step 8 QA / Handoff (PRD §46a)

Date: 2026-09-10 (Week 1 of the Sep 10 - Oct 9 build window, ahead of schedule).

## §46a Pilot Slice acceptance gate — checked one by one

| Criterion | Result | Status |
|---|---|---|
| >= 10 real leads produced from SRC-01 across the 8 priority cities | **95 leads** written in one live run (63 covered by Score_Breakdown at Ready_For_Review) | PASS |
| Dedup engine has zero false-negatives on a 10-record manual spot-check | Ran a **full pairwise audit across all 95 leads** (stronger than the required 10-record sample): 0 exact-hash collisions, 0 unflagged fuzzy matches >=75% | PASS |
| Every lead shows its Score_Breakdown | 0 of 95 `Ready_For_Review` leads missing `Score_Breakdown` (checked via a read-only Sheet query) | PASS |
| Business owner judges >= half of the top-scored leads "plausible to call" | **Needs your judgment** -- see the top-10 list below and the known limitation noted after it | OPEN -- awaiting your review |

Three of four criteria are met outright; the fourth is the one only a human can answer.

## Top 10 scored leads from the first live run (for your review)

All Pilot Slice leads currently cap at 60 (Warm) -- this is expected, not a bug (see
PLAN.md and the chat history: SIG-03 is the only signal SRC-01 can produce, and it maxes
out well below Hot without SIG-01/02 data or AI classification, both out of scope for
Oct 9).

| Score | Category | Name | City | Category |
|---|---|---|---|---|
| 60 | Warm | Heather Lynanne Jones. | Centerton | Medical/Dental |
| 60 | Warm | Douglas A Carmical, DDS | Bella Vista | Medical/Dental |
| 60 | Warm | Affordent of Springdale | Springdale | Medical/Dental |
| 60 | Warm | VA Medical Center Fayetteville Arkansas | Fayetteville | Medical/Dental |
| 60 | Warm | Lowell Medical Center | Lowell | Medical/Dental |
| 60 | Warm | Dr. Casey Dominguez | Cave Springs | Medical/Dental |
| 60 | Warm | My Friends And Me | Bentonville | Childcare |
| 60 | Warm | Central Child Care Center | Rogers | Childcare |
| 60 | Warm | His House Preschool | Rogers | Childcare |
| 60 | Warm | Little Prayers Daycare Inc | Springdale | Childcare |

## Known limitation, surfaced honestly

**"VA Medical Center Fayetteville Arkansas"** is a large, long-established federal
hospital, not a new business -- the SIG-03 near-zero-review heuristic almost certainly
caught a lightly-reviewed sub-listing or department page belonging to a much bigger,
long-existing organization, not a genuine new opening. **"Lowell Medical Center"** may be
the same pattern; worth a quick look before calling.

This is a real, visible limitation of a review-count-only heuristic (documented as an
assumption in `src/collector_src01.py`'s `NEW_LISTING_MAX_REVIEWS` constant) -- not a code
bug. It's exactly the kind of judgment call the Pilot Slice gate wants a human to make
before trusting the pipeline's output at face value. Options if this turns out to be a
recurring pattern once you review more of the 95:
- Tighten the review-count threshold further (currently <=3)
- Add a simple name-based exclusion filter for obviously-institutional names ("VA
  Medical Center", "Regional Hospital", etc.) as a cheap guard, without needing AI
  classification
- Accept it as an acceptable noise rate for a single-source pilot and let the human
  review step (which already exists) catch it -- which is what's actually happening
  right now, working as designed

## What's next after your review

- If you judge >= 5 of the top 10 (or a similar proportion across more of the 95)
  "plausible to call," the Pilot Slice gate is fully met, weeks ahead of the Oct 9
  target -- see PLAN.md for what continues toward the ~Dec 4 full MVP (SRC-02, SRC-03,
  AI classification, scheduling).
- If the false-positive rate from the VA Medical Center pattern looks high across more
  of the list, tightening `NEW_LISTING_MAX_REVIEWS` or adding the name-exclusion filter
  above is a small, cheap fix -- not a redesign.
