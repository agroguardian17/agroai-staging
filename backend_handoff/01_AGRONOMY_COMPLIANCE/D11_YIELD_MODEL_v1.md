# D11 Yield Model — Full Spec v1.0

**Domain:** D11 — Yield estimation, U-value register, gap attribution
**Owner:** Kuldip — Agronomy Compliance Owner
**Date:** 2026-09-23
**Backend contract:** implement §5 pipeline, §6 tables, §7 API. Season 1 uses process-baseline only; ML residual activates Season 2.

---

## 1. Purpose

D11 answers three questions per plot:

1. **Where is this crop heading?** — mid-season and end-of-season yield estimate with a 90 % band
2. **Which factors are pulling it down?** — per-factor attribution of the yield gap
3. **What is unexplained?** — residual pointing to missing data, missing rules, or missing agronomy

Without D11 the KB fires advisories but never measures whether the crop is actually on track. With D11, every stored season becomes calibration data for the next.

---

## 2. Architecture — hybrid model

```
                 ┌──────────────────────┐
                 │ Variety potential    │
                 │ (Y_var)              │
                 └──────────┬───────────┘
                            │
                 ┌──────────▼───────────┐
                 │ Site index           │
                 │ (SI, 0-1)            │
                 └──────────┬───────────┘
                            │
             Y_potential = Y_var × SI
                            │
                 ┌──────────▼──────────────────┐
                 │ Per-stage deficit           │
                 │ multiplicative engine       │
                 │  Y_process = Y_potential ×  │
                 │  ∏(1 − u_i × I_i)           │
                 └──────────┬──────────────────┘
                            │
                 ┌──────────▼───────────┐
                 │ ML residual layer    │
                 │ (Season 2+)          │
                 │  ε_ML                │
                 └──────────┬───────────┘
                            │
             Y_final = Y_process + ε_ML
                            │
                 ┌──────────▼───────────┐
                 │ Attribution engine   │
                 │ - Explained loss     │
                 │ - Unexplained loss   │
                 └──────────────────────┘
```

**Phase 1 (Season 1):** `ε_ML = 0` (no data to train on). `Y_final = Y_process`.
**Phase 2 (Season 2+):** ML residual trained on paired (predicted, actual) yield pairs from Season 1.

---

## 3. Component definitions

### 3.1 Variety potential — `Y_var`

Maximum achievable yield for the variety under ideal management + soil + climate. From institutional sources (source_tier L1).

| Variety | Y_var (t/ha fresh) | Y_var (q/acre fresh) | Source | Verification |
|---|:---:|:---:|---|:---:|
| IISR Mahima | 23.2 | 94 | ICAR-IISR profile | CONFIRMED |
| IISR Varada | 22.6 | 91 | ICAR-IISR profile | CONFIRMED |
| Nadia (local) | 20.0 | 81 | VNMKV OFT indicative | PROVISIONAL |
| Himachal (local) | 18.0 | 73 | VNMKV OFT indicative | PROVISIONAL |
| Rio-de-Janeiro | 24.5 | 99 | ICAR-IISR profile | CONFIRMED |

Add row as new varieties onboard. Backend seeds `variety_potential` table.

### 3.2 Site index — `SI`

Site-specific ceiling multiplier: how close this plot can approach `Y_var` given its soil + water + climate zone. Range: 0.30 (harsh) to 1.00 (ideal).

**Season 1 formula (heuristic, agronomist-authored):**

```
SI = SI_soil × SI_water × SI_climate

SI_soil = {
    black_vertisol_with_drip_broad_ridge     : 1.00,
    black_vertisol_with_drip_flat            : 0.85,
    black_vertisol_flood_irrigated           : 0.55,   -- soft-rot risk baked in
    red_loam_with_drip                       : 0.90,
    red_loam_without_drip                    : 0.70,
    sandy_loam_with_drip                     : 0.80,
    laterite                                 : 0.50,   -- not native ginger geography
    other                                    : 0.65
}

SI_water = {
    assured_source_year_round                : 1.00,
    assured_source_seasonal_gap              : 0.85,
    marginal_source                          : 0.65,
    rain_dependent_only                      : 0.40
}

SI_climate = {
    within_kannad_zone                       : 1.00,   -- baseline zone
    marathwada_west (Ahmadnagar/Beed)        : 0.90,
    marathwada_east (Nanded/Hingoli)         : 0.95,
    outside_marathwada                       : 0.75    -- provisional until validated
}
```

**Season 2+ update:** replace multiplicative heuristic with an ML site-index regressor trained on (soil test, water source, cluster station rainfall, actual yield) tuples.

**Y_potential = Y_var × SI**

### 3.3 U-value register — the 15-factor list

Each factor `i` has a `u_i` (fraction of yield potential lost if factor is fully expressed) and an intensity function `I_i(season)` ∈ [0, 1] measured from season records.

| # | Factor | `u_i` (EST) | Sub-node / signal | `I_i` definition | Recoverable? |
|:---:|---|:---:|---|---|:---:|
| 1 | Soft rot (Pythium) | 0.60 | D06-SR signals + saturation-hours | fraction of plot with confirmed rot symptoms | No, same season |
| 2 | Drainage failure / waterlogging > 48h | 0.35 | D03-WL saturation-hours + SAR | (waterlog_events × avg_duration) / 96h normalised | Partially |
| 3 | Bacterial wilt (once present) | 0.50 | D06-BW-001 field history + confirmed diagnosis | fraction of plot with wilt | No |
| 4 | K deficiency uncorrected in G2-G3 | 0.20 | D04 K budget - actual K applied | (budget_gap / budget_target) capped at 1.0 | Partially in G2 |
| 5 | Rhizome fly damage | 0.15 | D05 scouting damage % | scouting_damage_pct / 100 | No |
| 6 | Seed rhizome vigour poor | 0.15 | D01 emergence % at DAP 25 | 1 − (emergence_pct / 90) | No |
| 7 | Drought during rhizome fill (G3-G4) | 0.20 | D03 stress-days in stage | stress_days / 30 | Partially |
| 8 | Excess N late (> DAP 120) | 0.08 | D04 N schedule vs actual | max(0, actual_N_after_120DAP / 30) | No |
| 9 | Heat stress > 35 °C sustained (3+ days) | 0.10 | D07 heat-day count | heat_day_count / 15 | No |
| 10 | Weed pressure uncontrolled | 0.10 | D08 weeding compliance | 1 − weeding_compliance_pct | Partially |
| 11 | Micronutrient (Zn/Fe) lock-out | 0.08 | D04 leaf tissue / D14 NR | (deficiency_severity: 0/0.5/1) | Yes |
| 12 | Nematode pressure | 0.12 | D06 nematode signal | 1 if confirmed else 0.3 if suspected | No |
| 13 | Late planting (> 15 June) | 0.20 | D01-PW-001 | days_late / 30 capped at 1.0 | No |
| 14 | Wrong drip design (heavy soil + close dripper) | 0.15 | D03-DS-001 | 1 if mismatch else 0 | No, plot-level |
| 15 | Herbicide damage after emergence | 0.40 | D08-WD-001 blocklist hit | 1 if herbicide applied post-emergence | No |

**Total ≠ sum.** Losses compound multiplicatively:

```
Y_process = Y_potential × ∏ (1 − u_i × I_i)   for i in 1..15
```

**Confidence:** each `u_i` is SRC-EST (source_tier L4) for Season 1. Row entries in `yield_u_values` table carry `confidence` and `source_ref`. Season 1 field data replaces with empirical `u_i` per factor.

**Interdependence groups (avoid double-counting):**

- {1, 2, 11}: soft rot ← drainage failure ← waterlogging → apply the group's max u_i × I_i once, not sum. Backend uses `interdependence_group` column.
- {8, 4}: excess N late + K deficit — biologically opposite, apply higher only.
- {14, 2}: wrong drip design amplifies drainage failure — apply max, not sum.

Group definitions in §6.2 table.

### 3.4 Intensity `I_i(season)` — how to compute

Every `I_i` is a function of season records + sensor data + advisory-classification history. Backend computes at every yield-prediction call. Bounded [0, 1].

Formula per factor is in the U-value table above. Nulls (missing data) → `I_i = null`, factor omitted from product with a `missing_factor_i` flag in the output.

### 3.5 ML residual `ε_ML`

Season 1: `ε_ML = 0`.

Season 2+ training set = Season 1 tuples of `(features, Y_process, Y_actual)`. Target: `ε_ML = Y_actual − Y_process`. Model: gradient boosting on 30-50 features (weather aggregates, satellite indices, sub-node summaries, advisory-compliance rate, cluster peers' actuals).

**Guardrails:**
- Cap `|ε_ML| ≤ 0.15 × Y_process` — the residual layer corrects, not overrides
- Temporal split: train on seasons N-1 and earlier, validate on season N-1's holdout plots, deploy for season N
- Field-level split: never train + test on same plot
- If model MAPE > 20 % on validation, revert to `ε_ML = 0` for that season

---

## 4. Confidence band — 90 %

Every prediction ships `(y_point, y_low_90, y_high_90)`.

**Season 1:** bootstrap from `u_i` uncertainty.

```
For 1000 Monte Carlo draws:
  For each factor i:
    u_i_draw = clip(N(u_i, u_i × 0.4), 0, 1)   # 40% CV on EST u_i values
    I_i_draw = clip(N(I_i, 0.1), 0, 1)         # ±0.1 measurement noise
  Y_draw = Y_potential × ∏(1 - u_i_draw × I_i_draw)
Result: y_low_90 = 5th percentile, y_high_90 = 95th percentile, y_point = median
```

**Season 2+:** replace bootstrap with ML-derived prediction interval when residual model is calibrated.

---

## 5. Pipeline — computation flow

```
predict_yield(plot_id, as_of_dap):

  1. Load plot record: variety, planting_date, soil_type, water_source, cluster
  2. Y_var         ← variety_potential[variety]
  3. SI            ← compute site_index(plot)         # §3.2
  4. Y_potential   ← Y_var × SI

  5. For each of 15 factors:
     I_i          ← compute intensity(plot, factor, as_of_dap)  # §3.3
     If I_i is null → factor skipped, flag missing_factor
  6. Apply interdependence groups (max per group, not sum)
  7. Y_process     ← Y_potential × ∏(1 - u_i × I_i)

  8. ε_ML          ← 0 if season == 1 else ml_residual_model.predict(features)
  9. Y_final       ← Y_process + ε_ML

  10. (y_low_90, y_high_90) ← bootstrap_ci(Y_potential, u_i, I_i, ε_ML)

  11. Attribution:
      For each factor i:
        loss_i    ← Y_potential × u_i × I_i        # marginal, uncompounded
      explained   ← sum(loss_i) capped at (Y_potential - Y_process)
      unexplained ← (Y_potential - Y_process) - explained
      residual_pct ← unexplained / (Y_potential - Y_process) if gap > 0 else 0

  12. Emit:
      {
        y_point, y_low_90, y_high_90,
        y_potential, y_process, epsilon_ml,
        attribution: [{factor_i, loss_i, source_ref, confidence}, ...],
        unexplained: {value, pct},
        model_version, data_quality, confidence, missing_factors: [...]
      }

  13. Log to yield_prediction_log
```

Call frequency: daily (silent). Farmer-visible: at DAP 90, DAP 150, and harvest.

---

## 6. Data model

### 6.1 `variety_potential`

```sql
CREATE TABLE variety_potential (
    variety           TEXT PRIMARY KEY,
    y_var_t_per_ha    NUMERIC(5,2) NOT NULL,
    y_var_q_per_acre  NUMERIC(5,1) NOT NULL,
    source_institution TEXT NOT NULL,
    source_ref        TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    updated_at        TIMESTAMPTZ DEFAULT now()
);
```

### 6.2 `yield_u_values`

```sql
CREATE TABLE yield_u_values (
    factor_id            SMALLINT PRIMARY KEY,       -- 1..15
    factor_name          TEXT NOT NULL UNIQUE,
    u_value              NUMERIC(4,3) NOT NULL CHECK (u_value BETWEEN 0 AND 1),
    intensity_definition TEXT NOT NULL,              -- computable expression
    recoverable          TEXT NOT NULL CHECK (recoverable IN ('yes', 'no', 'partial')),
    signal_domain        TEXT NOT NULL,              -- D01..D14
    signal_rules         TEXT[],                    -- rule IDs the factor derives from
    interdependence_group TEXT,                     -- 'soft_rot_cluster' etc.
    confidence           NUMERIC(3,2) NOT NULL,
    source_tier          TEXT NOT NULL,              -- L1..L4
    source_ref           TEXT NOT NULL,
    calibration_status   TEXT NOT NULL,              -- 'EST_phase_1' | 'CALIBRATED_season_N'
    updated_at           TIMESTAMPTZ DEFAULT now()
);
```

Seed with 15 rows from §3.3 table above.

### 6.3 `site_index_config`

Holds the SI heuristic tables until Season 2 ML replaces. Read at every predict call.

```sql
CREATE TABLE site_index_config (
    dimension    TEXT NOT NULL,             -- 'soil', 'water', 'climate'
    key          TEXT NOT NULL,
    value        NUMERIC(3,2) NOT NULL CHECK (value BETWEEN 0.3 AND 1.0),
    updated_at   TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (dimension, key)
);
```

Seed from §3.2 heuristic.

### 6.4 `yield_prediction_log`

Every prediction call writes a row.

```sql
CREATE TABLE yield_prediction_log (
    id                BIGSERIAL PRIMARY KEY,
    plot_id           UUID NOT NULL REFERENCES plots(id),
    season_id         UUID NOT NULL REFERENCES crop_seasons(id),
    as_of_dap         INT NOT NULL,
    as_of_date        DATE NOT NULL,
    y_potential       NUMERIC(6,2) NOT NULL,       -- q/acre
    y_process         NUMERIC(6,2) NOT NULL,
    epsilon_ml        NUMERIC(6,2) NOT NULL DEFAULT 0,
    y_point           NUMERIC(6,2) NOT NULL,
    y_low_90          NUMERIC(6,2) NOT NULL,
    y_high_90         NUMERIC(6,2) NOT NULL,
    attribution       JSONB NOT NULL,               -- [{factor_id, loss, source_ref, confidence}, ...]
    unexplained_pct   NUMERIC(4,1) NOT NULL,
    missing_factors   INT[] NOT NULL DEFAULT '{}',
    data_quality      TEXT NOT NULL,                -- 'good' | 'partial' | 'sparse'
    model_version     TEXT NOT NULL,
    confidence        NUMERIC(3,2) NOT NULL,
    computed_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON yield_prediction_log (plot_id, as_of_date);
CREATE INDEX ON yield_prediction_log (season_id);
```

### 6.5 `yield_actual`

End-of-season truth capture (from D09-YD-002).

```sql
CREATE TABLE yield_actual (
    plot_id           UUID NOT NULL REFERENCES plots(id),
    season_id         UUID NOT NULL REFERENCES crop_seasons(id),
    fresh_q_per_acre  NUMERIC(6,2),
    dry_q_per_acre    NUMERIC(6,2),
    dry_ratio         NUMERIC(4,3),
    harvest_date      DATE NOT NULL,
    reported_by       TEXT NOT NULL,
    verified          BOOLEAN NOT NULL DEFAULT false,
    verified_by       TEXT,
    captured_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (plot_id, season_id)
);
```

Season-end reconciliation compares this to `yield_prediction_log` at DAP 150 and harvest.

---

## 7. API — the one function backend builds

```python
def predict_yield(plot_id: UUID, as_of_dap: int) -> YieldPrediction:
    """
    Returns:
      YieldPrediction {
        y_point:        float,     # q/acre
        y_low_90:       float,
        y_high_90:      float,
        y_potential:    float,
        attribution:    List[FactorLoss],   # per-factor loss with source
        unexplained:    {value: float, pct: float},
        data_quality:   'good' | 'partial' | 'sparse',
        confidence:     float,     # 0-1 overall confidence
        model_version:  str,       # 'D11-v1-EST-phase-1'
        missing_factors: List[int],
        computed_at:    datetime
      }
    """
```

**Contract:**
- Never returns null — sparse data → wider `y_low_90 / y_high_90` band + `data_quality='sparse'`
- Never returns a point estimate outside `[y_low_90, y_high_90]`
- Attribution always sums to explained gap; unexplained is separate field
- Missing factors listed explicitly, not silently dropped

---

## 8. Farmer-facing output — Marathi

Point estimate is not shown to farmer. Only the band + top 3 factors + one guidance line.

**Template at DAP 90 (mid-season):**

```
अपेक्षित उत्पन्न: {y_low_90}–{y_high_90} क्विंटल/एकर (हंगामाच्या मध्यावर, ६०% विश्वास)

सर्वात मोठे तीन कारणे:
1. {factor_1_mr}: {loss_1} क्विंटल कमी
2. {factor_2_mr}: {loss_2} क्विंटल कमी
3. {factor_3_mr}: {loss_3} क्विंटल कमी

पुढील ३० दिवसांत कोणते जोखीम टाळता येईल?
{advisory_recovery_action_mr}
```

Never present a single number. Never guarantee yield (D12-POS-* immutable). "अपेक्षित" not "निश्चित".

---

## 9. Season evolution

| Season | What changes |
|:---:|---|
| Season 1 (2026-27) | Process-only. `ε_ML = 0`. All `u_i` from EST. `SI` from heuristic. |
| Season 2 (2027-28) | Empirical `u_i` for top-5 factors. `ε_ML` activates if 100+ (predicted, actual) pairs. |
| Season 3 (2028-29) | ML site-index regressor replaces heuristic. All `u_i` empirical. |
| Season 4+ | Full hybrid model; process + ML calibrated. Confidence >= 0.85 sustained. |

Each season's model version tagged in `yield_prediction_log.model_version`. Rollback path: force `model_version` = older version, no code change.

---

## 10. Validation metrics (monthly report to KB author + backend)

| Metric | Formula | Target Season 1 | Target Season 3 |
|---|---|:---:|:---:|
| MAE (q/acre) | mean(|y_pred − y_actual|) at harvest | ≤ 15 | ≤ 8 |
| RMSE (q/acre) | sqrt(mean((y_pred − y_actual)²)) | ≤ 20 | ≤ 12 |
| Bias | mean(y_pred − y_actual) | |bias| ≤ 5 | |bias| ≤ 3 |
| Coverage-90 | fraction of actuals inside [y_low_90, y_high_90] | ≥ 0.80 | ≥ 0.88 |
| Attribution accuracy | fraction of top-3 factors matching agronomist post-mortem | ≥ 0.60 | ≥ 0.80 |
| Unexplained median | median(unexplained_pct) at harvest | ≤ 25% | ≤ 15% |

If any metric misses target for 2 consecutive months, model version freezes and calibration cycle triggers.

---

## 11. Data leakage guardrails (AG-V2.0 §51-52)

Absolute rules for the ML residual layer:

- **No harvest-derived features** as inputs for pre-harvest predictions
- **No advisory-classification** features from Season N in Season N's predictions (that's post-hoc)
- **No cluster peer's actual yield** as input until that peer has completed harvest
- **No leaf-tissue lab results** from post-harvest as input for pre-harvest calls
- Data timestamps enforced at feature-extraction time — any feature with `captured_at > as_of_date` is dropped

Backend implements a `feature_freshness_gate(feature, as_of_date)` function that all ML features flow through. Fail-closed.

---

## 12. What this replaces / supersedes

- `KB_DB_STATUS.md §3.2` — "define the yield model" → this document
- `AGRONOMY_SIGNOFF.md §2` — high-level model summary; superseded by this full spec
- 11 D11 fields marked "engine yield-model output" — populated by §7 API return
- 34 D11 rules total — reviewed against this spec; those that operate on yield outputs use the fields defined here

---

## 13. Standing agronomy rules

Enforced throughout D11:
1. Never present point estimate as fact — always show band + top-3 factors
2. Never guarantee yield to farmer — D12-POS-* immutable
3. Every prediction tagged with `model_version` and `data_quality`
4. Attribution transparent — farmer + agronomist see exactly which factors contribute
5. Unexplained residual visible, not buried — >25% flags agronomist review
6. Data leakage gate enforced code-side, not by convention

---

## 14. Open items

| ID | Item | Owner | Blocking? |
|---|---|---|:---:|
| D11-OI-01 | Season 1 field data collection for empirical `u_i` recalibration | Field ops | Season 2 model |
| D11-OI-02 | Variety potential rows for Nadia/Himachal — VNMKV verification | Kuldip + VNMKV | Provisional OK for Season 1 |
| D11-OI-03 | ML residual training pipeline (Season 2 activation) | Backend + data science | Season 2 launch |
| D11-OI-04 | Site-index climate zones outside Marathwada — expansion validation | Agronomy | Multi-region expansion |
| D11-OI-05 | Attribution accuracy validation — agronomist post-mortem template | Kuldip | Monthly metric coverage |
| D11-OI-06 | Feature-freshness gate implementation and tests | Backend | Season 2 ML activation |

---

## 15. Sign-off

Spec authored by Kuldip — Agronomy Compliance Owner, 2026-09-23.

Backend can implement §5 pipeline, §6 tables, §7 API today. Season 1 runs process-only (no ML). ML residual activates only when Season 1 delivers 100+ paired (predicted, actual) tuples.

Any deviation from §3 U-value definitions or §11 leakage guardrails must come back to agronomy for approval.

— Kuldip
Agronomy Compliance Owner
VIRAAI / Agro-Guardian AI

*End of D11_YIELD_MODEL_v1.md v1.0*
