# D12 Advisory-QA Workflow — Full Spec v1.0

**Domain:** D12 — Advisory Quality & Self-Assessment
**Owner:** Kuldip — Agronomy Compliance Owner
**Date:** 2026-09-23
**Backend contract:** implement the 4 tables in §3, 1 function in §5, and the review UI in §6.
**Deferred:** UI wireframe from backend can refine §6 field labels; agronomy will re-review then. Spec itself is production-ready.

---

## 1. Purpose

D12 makes the system honest about itself. It:
- Distinguishes true positives from false alarms
- Captures why farmers do not act on advisories
- Records agronomist bias observations for KB tuning
- Labels farmer-submitted photos into D06 diagnostic categories
- Assigns plots to clusters for peer-baseline comparison

Every output feeds back into KB improvement (rule tuning, threshold recalibration, new-rule authoring). Without D12, the KB drifts and no one knows.

---

## 2. The workflow — human view

**Cadence:** Weekly, every Monday 10:00–11:30 IST.
**Agronomist:** Reviews the past week's advisories for 3–5 randomly-selected farmers via a 20–30 min call each.
**Farmer:** Answers per-advisory: acted / not acted / partially. If not acted, reason.
**Photos:** Farmer-uploaded WhatsApp photos accumulate in a labelling backlog. Agronomist labels 10–20 per week during the same window.

**One-line rule:** every advisory that fired last week gets a 3-state classification before next Monday.

---

## 3. Data model — 4 tables + 1 config

### 3.1 `advisory_classification`

Every fired advisory gets one row per weekly review.

```sql
CREATE TABLE advisory_classification (
    id                    BIGSERIAL PRIMARY KEY,
    advisory_id           BIGINT NOT NULL REFERENCES advisory_log(id),
    plot_id               UUID NOT NULL REFERENCES plots(id),
    farmer_id             UUID NOT NULL REFERENCES farmers(id),
    rule_id               TEXT NOT NULL,
    fired_at              TIMESTAMPTZ NOT NULL,
    review_week           DATE NOT NULL,             -- Monday of review week
    classification        TEXT NOT NULL CHECK (classification IN (
                            'confirmed_true_positive',
                            'false_positive',
                            'unresolved'
                          )),
    evidence_source       TEXT CHECK (evidence_source IN (
                            'farmer_report',
                            'agronomist_visit',
                            'photo',
                            'sensor',
                            'no_evidence'
                          )),
    classification_note   TEXT,                       -- Marathi free-text
    reviewer              TEXT NOT NULL,              -- agronomist name
    reviewed_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (advisory_id, review_week)                 -- one classification per advisory per week
);

CREATE INDEX ON advisory_classification (rule_id, classification);
CREATE INDEX ON advisory_classification (review_week);
```

**State transitions:**
- `unresolved` → `confirmed_true_positive` OR `false_positive` in a later week when evidence arrives
- Once `confirmed_true_positive` or `false_positive`, never overwritten (audit trail)
- Amendment: insert a new row with same `advisory_id` and later `review_week`; the latest row wins for reporting

### 3.2 `non_compliance_reason`

Only populated when farmer did not act (or partially acted) on the advisory.

```sql
CREATE TABLE non_compliance_reason (
    id                    BIGSERIAL PRIMARY KEY,
    advisory_id           BIGINT NOT NULL REFERENCES advisory_log(id),
    plot_id               UUID NOT NULL REFERENCES plots(id),
    farmer_id             UUID NOT NULL REFERENCES farmers(id),
    action_state          TEXT NOT NULL CHECK (action_state IN (
                            'not_acted', 'partially_acted'
                          )),
    reason                TEXT NOT NULL CHECK (reason IN (
                            'already_done',
                            'cost_barrier',
                            'unavailable_input',
                            'disagreed',
                            'forgot',
                            'other'
                          )),
    reason_detail_mr      TEXT,                      -- Marathi free-text if 'other' or clarification needed
    captured_via          TEXT NOT NULL CHECK (captured_via IN (
                            'whatsapp_reply',
                            'agronomist_call',
                            'farmer_app',
                            'field_visit'
                          )),
    captured_by           TEXT NOT NULL,              -- agronomist or 'farmer_self'
    captured_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (advisory_id)                              -- one reason per non-compliant advisory
);

CREATE INDEX ON non_compliance_reason (reason);
CREATE INDEX ON non_compliance_reason (farmer_id);
```

**Semantics of the 6 reasons:**

| Code | Marathi | When to use |
|---|---|---|
| `already_done` | "आधीच केले" | Farmer had done the action before advisory fired |
| `cost_barrier` | "खर्च परवडत नाही" | Farmer couldn't afford input/labour cost |
| `unavailable_input` | "निविष्ठा उपलब्ध नाही" | Farmer tried, input not in local market |
| `disagreed` | "पटले नाही" | Farmer disagreed with the advice (agronomist follows up) |
| `forgot` | "विसरलो" | Simple omission |
| `other` | "इतर" | Anything else — free-text mandatory |

### 3.3 `bias_observation`

Agronomist notes on patterns across advisories — over-issuing, under-issuing, subtle wrongness.

```sql
CREATE TABLE bias_observation (
    id                    BIGSERIAL PRIMARY KEY,
    observed_week         DATE NOT NULL,             -- Monday of observation week
    bias_type             TEXT NOT NULL CHECK (bias_type IN (
                            'over_issuing',
                            'under_issuing',
                            'wrong_timing',
                            'wrong_target_group',
                            'wrong_wording',
                            'confidence_miscalibrated',
                            'other'
                          )),
    scope_domain          TEXT,                       -- D01..D14 if identifiable
    scope_rule_id         TEXT,                       -- specific rule if identifiable
    scope_plot_ids        TEXT[],                    -- affected plot subset
    observation_mr        TEXT NOT NULL,             -- Marathi free-text
    suggested_change_mr   TEXT,                       -- optional agronomist suggestion
    observed_by           TEXT NOT NULL,             -- agronomist name
    observed_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    kb_author_read        BOOLEAN NOT NULL DEFAULT false,
    kb_author_action      TEXT                        -- filled when KB author acts
);

CREATE INDEX ON bias_observation (observed_week);
CREATE INDEX ON bias_observation (scope_rule_id) WHERE scope_rule_id IS NOT NULL;
CREATE INDEX ON bias_observation (kb_author_read) WHERE kb_author_read = false;
```

**Weekly digest:** every Sunday, KB author gets the week's `bias_observation` rows where `kb_author_read = false`. Author sets `kb_author_action` when they've read + decided.

### 3.4 `photo_label`

Farmer-submitted symptom photos labelled by agronomist.

```sql
CREATE TABLE photo_label (
    id                    BIGSERIAL PRIMARY KEY,
    photo_id              UUID NOT NULL REFERENCES farmer_photos(id),
    plot_id               UUID NOT NULL REFERENCES plots(id),
    farmer_id             UUID NOT NULL REFERENCES farmers(id),
    submitted_at          TIMESTAMPTZ NOT NULL,      -- when farmer sent it
    label                 TEXT NOT NULL CHECK (label IN (
                            'soft_rot',
                            'bacterial_wilt',
                            'rhizome_fly',
                            'thrips',
                            'mite',
                            'leaf_spot',
                            'heat_scorch',
                            'zn_deficiency',
                            'fe_deficiency',
                            'k_deficiency',
                            'n_deficiency',
                            'waterlogging_damage',
                            'herbicide_damage',
                            'healthy',
                            'other',
                            'cannot_tell_from_photo'
                          )),
    label_confidence      NUMERIC(3,2) CHECK (label_confidence BETWEEN 0 AND 1),
    label_note_mr         TEXT,                       -- Marathi note
    labelled_by           TEXT NOT NULL,             -- agronomist name
    labelled_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    routed_to_advisory    BIGINT REFERENCES advisory_log(id),  -- if label triggered an advisory
    UNIQUE (photo_id)
);

CREATE INDEX ON photo_label (label);
CREATE INDEX ON photo_label (labelled_at);
```

**Labels align with D06 differential-diagnosis categories.** Labels do NOT drive automatic advisories in Season 1 — they build training data. From Season 3+, if `label_confidence >= 0.85` and label matches an active D06 branch, the mapper may auto-escalate (this is a Phase 2 decision).

### 3.5 `cluster_config` (small config table)

Backing config for the cluster-assignment function.

```sql
CREATE TABLE cluster_config (
    key                   TEXT PRIMARY KEY,
    value                 TEXT NOT NULL,
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed values:
INSERT INTO cluster_config VALUES
    ('min_plots_per_cluster', '8'),
    ('max_plots_per_cluster', '12'),
    ('proximity_km', '3'),
    ('planting_week_bucket_days', '7'),
    ('variety_gate', 'strict');    -- 'strict' = must match variety; 'loose' = variety-agnostic
```

---

## 4. Workflow specifications

### 4.1 Weekly-review call — agronomist protocol

```
Every Monday, 10:00–11:30 IST:

  1. Open review UI. System pre-selects 3-5 farmers via weighted random
     (§5 selection algorithm).

  2. For each farmer:
     a. Call the farmer (WhatsApp voice preferred, phone fallback).
     b. Read the advisory list from past week to farmer, one at a time.
     c. Ask: "हे तुम्ही केले का?"
        - If yes → mark confirmed_true_positive OR partial (depending on outcome)
        - If no → mark not_acted + capture reason from 6-value enum
     d. If farmer says "काहीच झाले नाही" or the diagnosis was wrong → false_positive
     e. Unclear? → unresolved, revisit next week
     f. Note down bias observations as they emerge (bias_observation row per
        pattern noticed, not per advisory).

  3. After all calls: open photo backlog. Label 10-20 unlabelled photos.

  4. Submit weekly report (auto-generated from rows written this session).
```

**Time budget per farmer:** 20–30 min. Total weekly: ~2 hours + 30 min photos + 30 min report review = **3 hours weekly for one agronomist to cover 3–5 farmers.**

Scaling: 1 agronomist per 20–25 farmers is the sustainable ratio for full weekly coverage (rotating which 3-5 get the call each week; every farmer reviewed at least once every 4-5 weeks).

### 4.2 Farmer selection algorithm

```
Weekly select N = 3 to 5 farmers, weighted by:
  + high advisory volume last week (want feedback where system talked most)
  + farmers not called in the last 4 weeks (fairness / coverage)
  + farmers with pending 'unresolved' classifications
  - farmers who have already declined feedback in past 2 weeks (rest period)

Random component: 30% pure random, 70% weighted — prevents predictability
and captures long-tail issues.
```

### 4.3 Non-compliance capture flow

Three entry paths, in order of preference:

1. **WhatsApp reply** — after an advisory fires, if farmer doesn't act within 3 days, the D12-AL-001 trigger sends: *"तुम्ही {action} केले का? हो / नाही / काही अंशी"*. Farmer replies. If नाही or काही अंशी, follow-up: *"कारण?"* with 6-button options.
2. **Agronomist call** — during weekly review, captured via UI form.
3. **Field visit** — agronomist notes reason in mobile field-visit form.

All three write to `non_compliance_reason` with different `captured_via` value.

### 4.4 Bias observation intake

Two intake modes:

- **In-line during review call:** UI has a "bias note" side-panel; agronomist types Marathi note + tags optional rule_id / domain.
- **Between calls:** standalone form for patterns spotted outside a specific farmer.

The KB author's weekly digest email (auto-generated Sunday 18:00 IST) lists all unread bias observations with counts by domain and rule. KB author reads, sets `kb_author_action` = "acknowledged", "rule-tuned", "rule-authored", "deferred", or "rejected-with-reason".

### 4.5 Photo labelling

Photos come in via WhatsApp forward to a dedicated agronomy number, or via farmer app upload. Backend routes to `farmer_photos` table with metadata (plot, farmer, timestamp, GPS if available).

**Labelling UI:** thumbnail grid, click-to-enlarge, radio-button label from the 16-value enum, optional confidence slider (default 1.0), Marathi note field.

**Batching:** agronomist labels in one sitting during weekly review — 10-20 photos per week is the steady rate. Backlog >30 triggers a bias observation ("photo throughput inadequate — need second agronomist or auto-triage").

### 4.6 Cluster assignment

Runs at plot enrollment; can be re-run on demand (e.g., after variety change).

**Algorithm (deterministic, no ML):**

```
def assign_cluster(plot):
    """Return existing cluster_id or 'NEW' to seed a new cluster."""
    candidates = []
    for cluster in active_clusters:
        # Gate 1: variety
        if config['variety_gate'] == 'strict' and cluster.variety != plot.variety:
            continue
        # Gate 2: planting week
        if abs((cluster.planting_week_median - plot.planting_week).days) > 7:
            continue
        # Gate 3: proximity
        distance_km = haversine(cluster.centroid, plot.polygon_centroid)
        if distance_km > 3.0:
            continue
        # Gate 4: capacity
        if cluster.plot_count >= config['max_plots_per_cluster']:
            continue
        candidates.append((cluster, distance_km))

    if candidates:
        # Pick nearest that has room
        return sorted(candidates, key=lambda x: x[1])[0][0].id

    # No fit → spawn new cluster
    return 'NEW'
```

**New-cluster spawn:** new cluster inherits the plot's variety, planting week, and centroid. When plot count in new cluster reaches `min_plots_per_cluster` (8), peer-baseline computation activates for D14 satellite rules.

**Fit score for outlier plots:** if a plot falls into a cluster with distance close to 3 km OR variety mismatch (in loose mode), compute a `cluster_fit_score` ∈ [0, 1] where 1.0 = perfect fit. Plots with fit_score < 0.6 get `INFORMATIONAL_ONLY` advisory class from D14 (existing rule D14-AN-002).

---

## 5. Backend functions

Three functions to build.

### 5.1 `classify_advisory(advisory_id, classification, evidence_source, note, reviewer)`

```python
def classify_advisory(advisory_id, classification, evidence_source, note, reviewer):
    """Write one row to advisory_classification for the current review week."""
    review_week = start_of_week(now(), weekday='MONDAY')
    advisory = get_advisory(advisory_id)
    insert('advisory_classification', dict(
        advisory_id=advisory_id,
        plot_id=advisory.plot_id,
        farmer_id=advisory.farmer_id,
        rule_id=advisory.rule_id,
        fired_at=advisory.fired_at,
        review_week=review_week,
        classification=classification,
        evidence_source=evidence_source,
        classification_note=note,
        reviewer=reviewer,
    ))
```

### 5.2 `capture_non_compliance(advisory_id, action_state, reason, detail, via, captured_by)`

Straightforward insert with FK checks; enforces `UNIQUE (advisory_id)`.

### 5.3 `assign_cluster(plot_id) → cluster_id | 'NEW_<cluster_id>'`

Algorithm in §4.6 above.

### 5.4 Weekly digest generator

Cron: every Sunday 18:00 IST. Emits:
- `weekly_report_{yyyy_mm_dd}.md` for the agronomist
- `bias_digest_{yyyy_mm_dd}.md` for the KB author

Contents auto-generated from the four tables — no manual step.

---

## 6. Review UI — spec for backend

**Screens:**

### 6.1 Weekly Review — landing
- List of 3–5 pre-selected farmers with advisory counts and pending items
- Buttons: "Start call" per farmer, "Skip week" per farmer
- Sidebar: photo backlog count, bias observations this week, unread digest

### 6.2 Per-farmer review
- Header: farmer name, plot(s), variety, DAP, cluster ID
- Table of advisories from past week:
  - Rule ID, fired-at, action text (Marathi), current classification
  - Buttons per row: ✅ True positive · ❌ False positive · ⏸ Unresolved
  - If ❌ or ⏸ or partial: dropdown for non-compliance reason
  - Free-text Marathi note field per row
- Bottom: "Save & next farmer" · "Bias note" (opens sidebar)

### 6.3 Photo labelling
- Grid of thumbnails from `farmer_photos` where no `photo_label` row exists
- Click → enlarged view with metadata
- Right panel: label dropdown (16 options), confidence slider, Marathi note
- "Save & next photo" button

### 6.4 Bias observation form
- Bias type dropdown (7 options)
- Scope: domain dropdown, rule ID autocomplete, plot IDs multi-select
- Marathi free-text: observation + suggested change
- Save

### 6.5 Weekly report preview
- Auto-generated: counts by classification, top false-positive rules, non-compliance reasons histogram, bias observation summary
- Agronomist button: "Send to KB author"

---

## 7. Success metrics — D12 as a subsystem

| Metric | Rule ID | Definition | Target |
|---|---|---|---|
| Action-compliance rate | D12-EVAL-001 | `confirmed_true_positive AND acted` / total advisories | ≥ 60% Season 1, ≥ 75% Season 3 |
| False-positive rate | D12-EVAL-002 | `false_positive` / total classified | ≤ 15% Season 1, ≤ 8% Season 3 |
| Classification coverage | D12-EVAL-003 | classified / total fired advisories | ≥ 70% Season 1, ≥ 90% Season 3 |
| Bias-to-action time | (derived) | median time from `bias_observation` to `kb_author_action` | ≤ 14 days |
| Photo backlog | (derived) | unlabelled photos > 7 days old | ≤ 20 at any time |

Metrics fire monthly review to KB author + product lead.

---

## 8. What this replaces / supersedes

- Prior D12 §3.3 in `KB_DB_STATUS.md` — "decide the advisory-QA workflow" → this document is the answer
- `AGRONOMY_SIGNOFF.md §3` — high-level summary; superseded by this full spec
- 8 D12 fields listed as "advisory-QA workflow" — this spec's tables populate them

---

## 9. Standing agronomy rules (from AGRONOMY_COMPLIANCE_v1.md §4)

Enforced throughout D12:
1. Every metric decomposable to raw rows in the 4 tables — no hidden aggregation
2. No silent field defaulting — nulls surface as `unresolved` or `not_captured`, not fabricated
3. Farmer voice preserved in Marathi; English translation only for KB author, never used as primary record
4. Non-compliance reason is data, not blame — never surfaced to farmer as accusation

---

## 10. Open items

| ID | Item | Owner | Blocking? |
|---|---|---|:---:|
| D12-OI-01 | Backend UI wireframe for §6 screens | Backend | No — spec is UI-agnostic |
| D12-OI-02 | Marathi voice-message templates for D12-AL-001 (WhatsApp reply prompts) | Kuldip + product | Season 1 launch |
| D12-OI-03 | Photo-label auto-suggestion (Phase 2) | ML team | No — Season 3+ |
| D12-OI-04 | Digest email routing (SendGrid config) | Ops | Weekly digest go-live |
| D12-OI-05 | Cluster fit-score threshold calibration | Season 1 field data | Season 2 |

---

## 11. Sign-off

Spec authored by Kuldip — Agronomy Compliance Owner, 2026-09-23.

Ready for backend implementation. UI wireframe (§6) can refine field labels but spec is architecturally locked. Any deviation from §3 table schema or §4 workflow must come back to agronomy for approval.

— Kuldip
Agronomy Compliance Owner
VIRAAI / Agro-Guardian AI

*End of D12_QA_WORKFLOW.md v1.0*
