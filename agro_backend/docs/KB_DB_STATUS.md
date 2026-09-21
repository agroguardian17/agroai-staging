# Ginger KB + Database — status for the agronomy team

**Date:** 2026-09-21 · **Audience:** agronomy team · **Owner:** backend

This is a plain-language status of the Ginger knowledge base (KB) and the
database (DB) behind it — what works today, what still needs your input, and
what is blocked on things outside software. No code knowledge assumed.

---

## 1. How the system fits together (the mental model)

There are three moving parts:

1. **The knowledge base (KB)** — your 481 agronomy rules ("if the crop is at
   this stage and this is happening, advise this"). The KB is **frozen**: we do
   not change your rules. It reads **346 distinct data fields** (soil type,
   rainfall, NDVI, pest counts, prices, and so on).
2. **The database (DB)** — where every fact about a farm, plot, season and
   reading is stored.
3. **The mapper** — the piece of software that, once a day, gathers everything
   the DB knows about a plot, computes what can be computed, and hands the KB a
   single tidy "farm brain" snapshot to run its rules against.

For a rule to actually produce advice, **four things** must all be true:

| Layer | Question | Whose job |
|---|---|---|
| 1. Home | Is there a place in the DB for this field? | Backend ✅ done |
| 2. Wired | Does the mapper carry it into the farm brain? | Backend ✅ done for 309/346 |
| 3. Data | Is there an actual value (entered, sensed, or computed)? | **Field ops + agronomy** |
| 4. Trigger | Is the rule's condition true today? | The crop/season |

**Key point:** "wired" is not the same as "firing." We have finished the
software (layers 1–2) for almost everything. Whether a rule *fires* now depends
mostly on layer 3 — is the data actually there — which is data entry, sensors,
and your sign-off, not more code.

---

## 2. What is completed ✅

**Field coverage: 309 of 346 fields (89%) are wired.**
**Rule readiness: 377 of 481 rules (78%) are "fully wireable"** — every field
they need is carried to the engine, so they will fire the moment their data is
present and their condition is true.

Readiness by domain:

| Domain | Ready to fire when data present | Partly ready | Fully blocked |
|---|---:|---:|---:|
| D01 nursery/stage | 21 / 22 | 1 | 0 |
| D02 land prep | 24 / 27 | 3 | 0 |
| D03 irrigation | 27 / 31 | 4 | 0 |
| D04 nutrients | 31 / 34 | 3 | 0 |
| D05 pests | 32 / 33 | 1 | 0 |
| D06 disease | 22 / 28 | 6 | 0 |
| D07 weather | 23 / 38 | 15 | 0 |
| D08 planting | 38 / 38 | 0 | 0 |
| D09 harvest | 39 / 39 | 0 | 0 |
| D10 schemes | 34 / 35 | 1 | 0 |
| D11 yield model | 5 / 34 | 18 | 11 |
| D12 advisory QA | 14 / 36 | 20 | 2 |
| D13 economics | 39 / 39 | 0 | 0 |
| D14 satellite | 28 / 47 | 11 | 8 |

What that means in practice, by data source:

- **Farm / plot / season facts** — soil, water source, irrigation, variety,
  planting dates, the full agronomy plan (beds, spacing, fertiliser splits,
  mulch stages, earthing-up, harvest plan). Entered on the **Data Entry** page.
- **Soil lab chemistry** — OC, EC, free lime, micronutrients. Entered on the
  **Lab Soil Test** page.
- **Pest & disease scouting** — incidence %, symptoms, trap counts, dig
  samples. Entered on the **Crop Scouting** page.
- **Season economics & operations & schemes** — costs, grades, prices, spray
  history, subsidy/scheme status. Entered on the **Season & Scheme Records**
  page.
- **Weather** — a daily forecast+past-weather feed (Open-Meteo) drives the
  rain-gap, dry-spell, effective-rainfall, evaporation and radiation fields,
  and we derive rainfall-deviation and a severe-weather (cyclone) proxy.
- **Satellite** — a daily Sentinel-1/2 sweep fills NDVI/NDRE/SAR indices and,
  once ≥3 plots in a cluster are enrolled, **peer/regional baselines** so a
  plot can be compared to its neighbours at the same growth stage.
- **Landsat land-surface temperature** — a daily USGS feed gives canopy
  temperature, from which we compute the crop water-stress index (CWSI).
- **Advisory compliance (new)** — the system now measures itself: how many
  advisories were issued, how many the farmer acted on, how many on time, and
  the **action-compliance rate** (your primary success metric, D12-EVAL-001).
- **WhatsApp delivery** — the full path to send a Marathi advisory to a farmer
  is built and tested end to end.

---

## 3. What still needs the agronomy team 📋

These are **not** software gaps — they are agronomy inputs only your team can
give. Software is ready and waiting.

### 3.1 Confirm the default values (quick, high value)
We applied sensible defaults so fields flow now, but nine of them need your
sign-off. Full list with the risk of each is in
[`docs/AGRONOMIST_REVIEW.md`](AGRONOMIST_REVIEW.md). The two that matter most:

- **PHI table (pre-harvest interval)** — food safety. We default to a
  conservative 21 days for any pesticide group we don't recognise. Please
  confirm the per-chemical PHI days and the group codes farmers actually enter.
- **Rainfall normals** — we use placeholder seasonal-rainfall figures per
  agro-climatic zone. Please replace them with real IMD district normals so the
  "rain deficit/surplus" advice is accurate.

Also confirm: soil-type mapping (esp. "red → laterite"), the agro-climatic zone
district list, and the growth-stage cut-points by days-after-planting.

### 3.2 Define the yield model (D11 — 11 fields, the biggest remaining piece)
The engine is meant to **predict end-of-season yield** and explain the gap
between predicted and achievable yield. To do that it needs a **yield model**:
a defined method that takes the season's conditions and outputs a yield
estimate, a confidence band, and an attribution of the shortfall to causes
(the "U-value" register — which limiting factors cost how much yield). This is
an agronomy / data-science artifact we cannot invent without producing
misleading numbers. **We need your team's definition** of:
- how to estimate yield from the season so far,
- the U-value list (each yield-limiting factor and its typical cost),
- how to split the yield gap into "explained" vs "unexplained."

Until then, 11 D11 fields stay empty and the yield-prediction rules wait.

### 3.3 Decide the advisory-QA workflow (D12 — 8 fields)
We just wired the four D12 counters that can be computed automatically. The
remaining eight need a **human review workflow** that does not exist yet:
- classifying alerts as true vs false alarms,
- recording bias observations and non-compliance reasons,
- photo upload + labelling,
- cluster assignment.

This is a "build a small review tool + process" decision, not field-wiring.
Tell us the workflow you want and we build it.

---

## 4. What is stuck / blocked 🚧 (and on what)

| Blocked on | Fields / capability affected | Who unblocks |
|---|---|---|
| **Enrolling ≥3 plots in a cluster** | Peer/regional NDVI+NDRE baselines (satellite comparison to neighbours) | Field ops (enrolment) |
| **Data entry not yet done** | Most of the 377 ready rules stay quiet until plot/season/scouting/economics data is entered | Field ops + agronomy |
| **WhatsApp go-live** | Advisory delivery to farmers — code is ready; waiting on Meta template approval + WhatsApp Business credentials | Ops / admin |
| **USGS credentials + job switch** | Landsat LST → CWSI (heat-stress advice) | Ops (free USGS account) |
| **Main Node weather station (hardware)** | On-site air temp/humidity/wind, `station_id`, data-age freshness | Hardware install |
| **Sub Node sensors (hardware)** | Live soil moisture / EC status fields, saturation-hours duration | Hardware install |
| **Time-series history accrues** | EC baseline & trend, forecast bias-correction, leaf-wetness / saturation durations | Time (needs weeks of data) |
| **One-off percolation field test** | `percolation_class`, `percolation_time_hours` | Field ops (simple test) |
| **Yield-model definition** | 11 D11 prediction fields | **Agronomy team (§3.2)** |

None of these is waiting on more mapper code.

---

## 5. The 37 fields not yet wired — at a glance

| Category | Count | Nature |
|---|---:|---|
| Engine yield-model output (D11) | 11 | Needs your yield-model definition (§3.2) |
| Advisory-QA workflow (D12) | 8 | Needs a human review tool/process (§3.3) |
| Hardware / runtime message-pipeline | 9 | Sub Node + compose-time flags |
| Derived (needs history or a field test) | 6 | EC trend, durations, percolation |
| Weather-station hardware / forecast bias | 3 | Main Node install + observed history |

Full field-by-field detail is in
[`docs/KB_SCHEMA_MAPPING.md`](KB_SCHEMA_MAPPING.md).

---

## 6. Bottom line

- The **software is essentially complete**: 309/346 fields wired, 377 rules
  ready to fire.
- The system now **delivers advice on WhatsApp** and **measures its own
  compliance** — the moment credentials and data are in place.
- The remaining work is **agronomy and operations, not code**: confirm the
  defaults, define the yield model, enable delivery, enter pilot data, and
  install the field hardware.
- The single highest-leverage agronomy input is the **yield-model definition**
  (§3.2) — it unblocks the entire D11 domain.
