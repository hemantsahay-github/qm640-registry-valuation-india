# Emergent.ai Build Script: Integrating the Circle-Rate Anchoring Research into Estima (estima.co.in)

**Owner:** Hemant Kumar Sahay · **Confidential — proprietary research IP** · Version 1.2, 16 October 2026 (adds Phase 7: live public-data feeds)
**Source research:** QM 640 Capstone, *Correcting for Circle-Rate Anchoring in Indian Residential Property Valuation*. Repository: `qm640-registry-valuation-india` (private).

This file is a sequence of prompts to paste into Emergent.ai, one phase at a time. Wait until each phase has been built and tested before pasting the next. Text in `[[double brackets]]` is filled in once the matching research stage is finished.

---

## How to use this script

1. Open the existing Estima project in Emergent (or a branch or copy of it, so the live site is not affected).
2. Paste **Phase 0** first. It gives Emergent the context and the guardrails, and it asks for a plan rather than code.
3. Paste Phases 1 to 7 in order. Each phase ends with acceptance tests. Ask Emergent to run them and show you the result before moving on.
4. Research dependencies:
   - Phases 1 and 2 can be built now, using placeholder data.
   - Phase 3 needs the RQ4 correction-factor table (Week 7).
   - Phase 4 needs the scoring endpoint (Week 8).
   - Phase 7 (live data feeds) can start now for data.gov.in and OpenStreetMap. The index panels need the research repo's `src/live` loaders to have run once.

| Phase | Builds | Depends on research stage | Earliest |
|---|---|---|---|
| 0 | Context, guardrails, plan | — | Now |
| 1 | Data layer + admin upload of research tables | Data dictionary (done) | Now |
| 2 | Fair Value Score calculator (UI + server logic, placeholder factors) | RQ1 definitions (done) | Now |
| 3 | Load real micro-market correction factors + market map | RQ4 output | Week 7 |
| 4 | Live model scoring through a private API | RQ3 model + FastAPI endpoint | Week 8 |
| 5 | Integration into Net Worth Dashboard, Transaction History Explorer, Rental Snowball Planner | Phases 2–4 | Week 8–9 |
| 6 | DPDP, IP protection, disclaimers, QA and release | All | Week 9–10 |
| 7 | Live public-data feeds: market index panel, locality data refresh, quarterly correction-factor refresh | `src/live/` connectors (done); study run for factors | Now (feeds) / after study run (factors) |

---

## Phase 0 — Context and guardrails (paste first)

```
You are extending my existing web app Estima (estima.co.in), an Indian real-estate
estimation and net-worth platform. Do NOT change existing features unless I ask.

NEW FEATURE: "Fair Value Score" — based on my proprietary research on circle-rate
(ASR / ready reckoner) anchoring in Maharashtra property registrations.

Research summary (for your understanding, do not display verbatim):
- Stamp duty is charged on the higher of declared consideration and the ASR value,
  so many registrations declare a value at (or very near) the ASR value even when
  the real price is higher. This is "anchoring".
- R = declared consideration / ASR value. A registration is "anchored" when
  0.98 <= R < 1.02.
- For each micro-market (village/locality), my research estimates a CORRECTION
  FACTOR CF = median(predicted fair value / registered value) for anchored deals.
- Fair value estimate for an anchored registration = registered value x CF.
- Pilot geography: Pune and Thane districts; FY 2023-24 to 2025-26.

Guardrails:
1. All research tables and model logic live SERVER-SIDE only. The browser receives
   only the final numbers for the user's own query. Never ship the full
   correction-factor table, coefficients or model files to the frontend.
2. DPDP Act 2023 compliance: collect the minimum data needed; no names, PAN or
   Aadhaar in this feature; explicit consent checkbox before saving any property;
   users can delete saved properties; log consent with timestamp.
3. Every result shows the disclaimer: "Indicative estimate based on statistical
   research on registered transactions. Not a valuation report, legal or
   financial advice."
4. Footer on every Fair Value page: "© 2026 Hemant Kumar Sahay. Fair Value Score
   methodology is proprietary."
5. Mobile-first, same design system, fonts and colours as the existing Estima app.

First, reply with: (a) your understanding, (b) the files/collections you will add
or change, (c) a phase plan. Do not write code yet.
```

## Phase 1 — Data layer and secure admin upload

```
Build the data layer for Fair Value Score.

Collections / tables (server-side only):
1. micro_markets
   - micro_market_id (string, slug e.g. "pune-baner")
   - district ("Pune" | "Thane"), micro_market_name (English), micro_market_mr (Marathi)
   - lat, lon (float)
   - asr_rate_m2_fy2526 (number, INR per m2 carpet) [optional, admin-entered]
2. correction_factors
   - micro_market_id, fy ("2023-24" | "2024-25" | "2025-26" | "pooled")
   - n_transactions (int), n_anchored (int), anchored_share (0-1)
   - cf_median (float), cf_ci_low (float), cf_ci_high (float)
   - cf_eb (float)  -> partially pooled factor for localities with few anchored deals; show
     it as "estimated from nearby localities" when reportable = false
   - reportable (bool)  -> false when n_anchored < 20 (show "insufficient data")
   - model_version (string), published_at (datetime)
3. fair_value_queries (user audit log, DPDP-minimal)
   - user_id, created_at, district, micro_market_id, carpet_area_m2, floor,
     new_sale (bool), parking (bool), registered_value_inr, result_json,
     consent_given (bool), consent_ts

Admin page /admin/fair-value-data (role = admin only, my account):
- Upload CSV for micro_markets and correction_factors (schemas above).
- Validate columns, types, ranges (cf_median between 0.8 and 3.0; anchored_share 0-1);
  show row-level errors; preview before commit; keep previous version for rollback.
- Store model_version; show "last updated" date.

Seed with PLACEHOLDER data for 5 Pune and 5 Thane micro-markets with
cf_median = 1.00 and reportable = false, clearly marked "PLACEHOLDER".

Acceptance tests:
- Non-admin cannot open the admin page or call its APIs (403).
- Upload with a missing column is rejected with a clear message.
- No API returns more than one micro-market's factor per request to a non-admin.
```

## Phase 2 — Fair Value Score calculator

```
Build page /fair-value (link it in the main navigation as "Fair Value Score").

Inputs (form):
- District (Pune/Thane), Locality (searchable dropdown from micro_markets; show
  English and Marathi names)
- Carpet area (m2 or sq ft toggle; convert sq ft -> m2 by / 10.7639; if user only
  knows built-up area, convert carpet = built-up / 1.2 and show a note)
- Floor (number), New sale from builder? (yes/no), Parking included? (yes/no)
- Registered value / agreement value in INR (Indian digit grouping, e.g. 1,25,00,000)
- Optional: ASR value from the agreement (INR). If blank, estimate it as
  asr_rate_m2 x carpet_area_m2 when asr_rate is available.

Server logic (POST /api/fair-value/score):
1. R = registered_value / asr_value (if asr_value known).
2. anchored = 0.98 <= R < 1.02.
3. Look up correction_factors for the micro_market (latest fy, else pooled).
4. If anchored and reportable: fair_value = registered_value x cf_median,
   range = registered_value x [cf_ci_low, cf_ci_high].
   If not anchored: fair_value = registered_value; message "This registration
   does not appear to be anchored to the circle rate."
   If not reportable: show "Not enough registrations in this locality yet."
5. Return: R, anchored flag, fair_value, range, cf, anchored_share of the
   locality, model_version, disclaimer.

Results card:
- Big number: "Estimated fair value: Rs X (range Rs A - Rs B)"
- "Your registered value is at Y% of the circle-rate value."
- Badge: "Likely anchored to circle rate" / "Not anchored" / "Insufficient data"
- Small gauge for R; one-line plain-English explanation; disclaimer; footer.
- Buttons: "Save to my portfolio" (requires consent checkbox), "Explain this".

Acceptance tests (unit tests on the server function):
- registered 50,00,000 / ASR 50,00,000, CF 1.20 reportable -> fair 60,00,000, anchored.
- registered 65,00,000 / ASR 50,00,000 -> R = 1.30, not anchored, fair = 65,00,000.
- cf reportable = false -> "insufficient data", no fair value number.
- sq ft 1076.39 -> 100.00 m2.
```

## Phase 3 — Real correction factors and locality map *(after RQ4, Week 7)*

```
Replace placeholders with the research output.
- I will upload correction_factors.csv (model_version = "[[RQ4 model version]]").
- Add a Locality Insights panel on /fair-value showing for the chosen locality only:
  anchored share, CF with range, number of registrations, last updated.
- Add a map (Leaflet + OpenStreetMap tiles, attribution "© OpenStreetMap
  contributors") with locality markers coloured by CF band
  (<1.05, 1.05-1.15, 1.15-1.30, >1.30). Clicking a marker shows only the band and
  the locality name, NOT the exact factor, unless the user is logged in.
- Hide markers where reportable = false.
Acceptance: map loads < 2 s on mobile; no endpoint exposes the whole table.
```

## Phase 4 — Live model scoring through a private API *(after Week 8)*

```
Connect to my private scoring service (FastAPI, built from the research repo).

POST {{SCORING_API_URL}}/v1/score   header: X-API-Key: {{SCORING_API_KEY}} (server env var only)
Request:
{ "district": "Pune", "micro_market": "Baner", "carpet_area_m2": 85.5,
  "floor_no": 12, "new_sale": 1, "parking": 1, "area_basis": 1,
  "fy": "2025-26", "registered_value_inr": 9500000, "asr_value_inr": 9300000 }
Response:
{ "predicted_value_inr": 11850000, "predicted_value_m2": 138596,
  "interval_inr": [10900000, 12800000], "r_ratio": 1.0215,
  "anchoring_probability": 0.41, "cf_locality": 1.22,
  "top_drivers": [ {"feature": "dist_cbd_km", "effect": "-"}, ... ],
  "model_version": "[[RQ3/RQ4 version]]" }

Rules:
- Call only from the backend; cache identical requests 24 h; time-out 5 s and fall
  back to the Phase 2 table method with a note "model temporarily unavailable".
- Show "anchoring_probability" as Low / Medium / High (<0.3, 0.3-0.6, >0.6).
- Show top_drivers as up to 3 plain-English reasons ("Closer to the city centre
  raises value").
- Rate-limit: 20 scores per user per day on the free tier.
```

## Phase 5 — Integrate with existing Estima modules

```
1. Net Worth Dashboard: for each saved property, add a "Fair value" column next
   to "Registered/purchase value" and use fair value (when available) in the
   net-worth total, with a toggle "Use registered value instead".
2. Property Transaction History Explorer: add R ratio and an "anchored" badge to
   each transaction row the user enters; add a filter "Show anchored only".
3. Rental Snowball Planner: rental yield = annual rent / fair value (show both
   yields: on registered value and on fair value).
4. Add an "Explain this" modal reused across all three modules (text below).
Do not change existing calculations when fair value is unavailable.
```

"Explain this" copy:
> Stamp duty in Maharashtra is charged on the higher of the declared price and the government's circle rate (ready reckoner). Many registrations are therefore declared at the circle rate even when the real price is higher. Estima's Fair Value Score uses research on registered transactions in your locality to estimate how far registered values usually understate the market. It is an indicative statistical estimate, not a valuation report.

## Phase 6 — DPDP, IP protection, QA and release

```
DPDP (Digital Personal Data Protection Act 2023 / Rules 2025):
- Consent notice in English and Marathi before saving any property: purpose,
  data stored, retention (until user deletes or 3 years of inactivity), contact
  for grievance (my e-mail), right to erase.
- "Delete my Fair Value data" button in profile; hard-delete within 24 h.
- No names, PAN, Aadhaar, phone in fair_value_queries.
- Keep server logs 90 days; mask IP addresses after 30 days.

IP protection:
- No bulk export of correction factors; robots.txt disallow /api/; add a
  per-user and per-IP rate limit; detect scraping (more than 100 localities per
  day) and block.
- Terms of Use clause: Fair Value Score methodology and data are proprietary to
  Hemant Kumar Sahay; no reproduction or model training permitted.
- Minify/obfuscate frontend bundle; no research terms in client code beyond labels.

QA:
- Run the Phase 2 unit tests + an end-to-end test (enter property -> score ->
  save -> appears in Net Worth Dashboard -> delete -> gone).
- Lighthouse mobile score >= 85; accessibility labels on all inputs.
- Release behind a feature flag "fair_value_v1" for my account first, then 100
  beta users, then all users.
```

---

## Phase 7 — Live public-data feeds *(feeds now; factor refresh after the study run)*

The research repository now has live connectors (`src/live/`) for every public source in the synopsis. Only **data.gov.in** and **OpenStreetMap** have official APIs. The RBI house price index (which covers Pune and Thane), NHB RESIDEX, IGR ready-reckoner rates and MahaRERA come from their official exports. Estima uses the *normalised files* produced by the research pipeline, plus the two real APIs directly.

```
Add a live-data layer to the Fair Value feature. Keep every API key on the SERVER
(environment variables); never call government APIs from the browser.

1. New collection market_index (server-side):
   - city ("Pune" | "Thane"), quarter ("FY26Q1" style), index (float),
     series ("RBI HPI (base 2022-23=100)" | "NHB RESIDEX HPI @ assessment price"),
     source (text), loaded_at (datetime)
   Admin upload on /admin/fair-value-data accepts the research files
   rbi_hpi.csv and residex.csv (exact columns: city, quarter, index, series, source).
   Optional: if env DATAGOVIN_API_KEY and DATAGOVIN_RBI_HPI_RESOURCE are set, a
   nightly server job calls
     GET https://api.data.gov.in/resource/{resource_id}?api-key={key}&format=json&offset=0&limit=500
   (paginate with offset until 'total' is reached), maps rows to market_index,
   and logs each call (URL with the key removed, status, row count).

2. "Market trend" panel on /fair-value, below the result card, for the chosen
   district only: a small line chart of the last 8 quarters of both series,
   latest year-on-year change, and the text
   "Source: RBI DBIE / NHB RESIDEX — official indices, updated quarterly".

3. Locality data refresh (OpenStreetMap, official open APIs):
   - Monthly server job: Overpass API (POST https://overpass-api.de/api/interpreter)
     for rail/metro stations in the Pune and Thane bounding boxes; Nominatim
     (https://nominatim.openstreetmap.org/search?format=jsonv2) for any new locality.
   - Max 1 request/second to Nominatim; User-Agent "Estima/1.0 (contact: {admin e-mail})";
     cache results; show "© OpenStreetMap contributors" on every map.
   - Update micro_markets.lat/lon and a new stations collection.

4. Quarterly correction-factor refresh (after each research pipeline run):
   - Admin uploads the new correction_factors.csv (model_version changes).
   - Keep the previous version for rollback; show "Factors updated: <date>,
     model <version>" on the Fair Value page.
   - Reject the upload if the file's model_version contains "synthetic" or the
     research RESULTS_LOG entry for that run is not labelled STUDY DATA.

5. Data-source status page /admin/data-sources (admin only): one row per source
   (IGR Index-II, IGR ASR, MahaRERA, NHB RESIDEX, RBI HPI, data.gov.in, OSM) with
   access route, last refresh, rows loaded, and next scheduled job.

Acceptance tests:
- With no API key set, the nightly job is skipped and logs "key missing" (no crash).
- Uploading a residex.csv with a missing 'quarter' column is rejected with a clear error.
- The Market trend chart shows only the selected district's series.
- No API key appears in any log line or browser network response.
- A correction_factors.csv whose model_version contains "synthetic" is rejected.
```

## Data hand-off checklist (research → Estima)

| File from research repo | Emergent collection | Produced by | Status |
|---|---|---|---|
| `data/external/osm/locality_gazetteer.csv`, `osm/stations.csv` | micro_markets, stations | `src/live/osm.py` (Overpass + Nominatim) | Code ready; current files are approximate seeds until `python -m src.live.fetch_all --run osm` is run |
| `data/external/rbi_dbie/rbi_hpi.csv` | market_index (Phase 7) | `src/live/rbi_hpi.py` (DBIE export or data.gov.in API) | Code ready; load the DBIE export |
| `data/external/residex/residex.csv` | market_index (Phase 7) | `src/live/nhb_residex.py` | Code ready; load the RESIDEX download |
| `outputs/rq4/external/summary.json` | "Factors validated against RBI / RESIDEX" note on the Fair Value page | `rq4_external_validation.py` (stage `rq4ext`) | Code ready; runs once an index file is loaded |
| `outputs/rq4/correction_factors.csv` | correction_factors (schema matches Phase 1; extra column `cf_eb` = shrunk factor for thin localities) | rq4_anchoring.py | Code ready; current file is SYNTHETIC — upload only after the study-data run |
| `outputs/rq1/rq1_by_segment.csv` | anchored_share by district/FY (marketing copy) | rq1_bunching.py | Pipeline validated; study run pending real data |
| `api/score_endpoint.py` (FastAPI) | Phase 4 private API | Week 8 | [[pending]] |

**Rule:** only files from runs labelled *STUDY DATA* in `docs/RESULTS_LOG.md` may be uploaded to Estima. Synthetic validation outputs must never go live.
