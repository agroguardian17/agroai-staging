# D03-WB Rules — Delivery Class Tagging

**Purpose:** Explicit `delivery_class` tag for each of the 8 D03-WB rules per backend's request. Delivery class controls: (a) how often a rule can re-fire, (b) whether farmer gets repeat notifications, (c) resolution triggers.

**Version:** 1.0
**Date:** 25 September 2026
**Owner:** Kuldip — Agronomy Compliance Owner
**Ref:** `D03_WATER_BUDGET_RULES.md` v1.0; Backend agronomy-inputs request §1f

---

## Delivery class definitions (glossary)

| Class | Meaning | Farmer message cadence |
|---|---|---|
| `EVENT` | Fires per discrete event (e.g., after every irrigation event) | Each firing = new message |
| `SILENT_GUARD` | Fires but emits no farmer message; data-only for downstream consumers (D11, dashboards) | Never messages farmer |
| `ONCE_UNTIL_RESOLVED` | Fires once, then suppresses re-fire until an explicit resolution condition met | Single message; no reminders until resolved |
| `WINDOW` | Fires within a DAP or stage window; adjusts downstream behaviour (e.g., dose scaling) for that window | May emit context messages at window boundaries |

---

## Per-rule tagging

| Rule ID | Delivery class | Resolution condition (for ONCE_UNTIL_RESOLVED) | Rationale |
|---|:---:|---|---|
| **D03-WB-001** | `EVENT` | — | Standard daily irrigation decision; fires each morning cron + on-demand |
| **D03-WB-002** | `ONCE_UNTIL_RESOLVED` | Farmer confirms irrigation done (dose logged) OR VWC returns to `ok` state | Red urgency; do not spam farmer if they've acted; re-fires only if situation persists after 24h without action |
| **D03-WB-003** | `EVENT` | — | Post-event warning; fires after each over-dose event (event-scoped, naturally one-per-event) |
| **D03-WB-004** | `EVENT` | — | Post-event correction; fires after each under-dose event |
| **D03-WB-005** | `SILENT_GUARD` | — | Daily D11 feeder; no farmer message ever |
| **D03-WB-006** | `ONCE_UNTIL_RESOLVED` | Water flow sensor reports a reading (any reading) → resolved | Hardware alert; don't spam farmer daily while sensor is dead; re-fires only after new gap of >3 days if sensor fails again |
| **D03-WB-007** | `WINDOW` | Applies for remainder of season after firing; reduces subsequent D03-WB-001 doses by 20% until DAP 240 | Season-total flag; not a discrete event; adjusts downstream behaviour |
| **D03-WB-008** | `ONCE_UNTIL_RESOLVED` | All geometry fields captured (planting_method, spacings, drip fields, sensor position all non-NULL) | Blocking gate; farmer sees one prompt, resolves via app; no repeat prompts |

---

## Additional delivery metadata

| Rule ID | Cron cadence | On-demand triggerable? | Push notification? |
|---|:---:|:---:|:---:|
| D03-WB-001 | Daily 05:00 IST | Yes | Standard (in-app + WhatsApp digest) |
| D03-WB-002 | Daily 05:00 IST + hourly re-eval | Yes | **Immediate WhatsApp push** |
| D03-WB-003 | Event-triggered (post-irrigation) | No | Standard |
| D03-WB-004 | Event-triggered (post-irrigation) | No | Standard |
| D03-WB-005 | Daily 23:00 IST (D11 aggregation cron) | No | None (silent) |
| D03-WB-006 | Daily 05:00 IST | No | **Immediate WhatsApp push** on first fire |
| D03-WB-007 | Weekly Sunday 18:00 IST | No | Standard |
| D03-WB-008 | On plot-setup submission event | Yes (farmer edits geometry) | In-app modal (blocking) |

---

## Resolution-condition detail (for ONCE_UNTIL_RESOLVED rules)

### D03-WB-002 (severe deficit RED)
```python
resolved_when = (
    (irrigation_event_logged_since_fire AND per_plant_dose_L >= variety_min_per_event_L)
    OR (vwc_status == 'ok' AND stage_water_deficit_L_per_plant < stage_water_target × 0.30)
    OR (rain_actual_since_fire >= 25)
)
# Re-fires if resolution lost AND 24h passed since last fire
```

### D03-WB-006 (sensor gap)
```python
resolved_when = (
    days_since_last_flow_reading <= 1
)
# Simple: any new reading resolves. Re-fires only if a new gap of >3 days occurs later.
```

### D03-WB-008 (geometry gate) — v1.1 corrected method-conditional check
```python
resolved_when = (
    planting_method IS NOT NULL
    AND (
        (planting_method IN ('broad_bed', 'raised_bed') AND bed_center_spacing_cm IS NOT NULL AND rows_per_bed IS NOT NULL)
        OR
        (planting_method IN ('furrow', 'flat') AND furrow_center_spacing_cm IS NOT NULL)
    )
    AND plant_spacing_within_row_cm IS NOT NULL
    AND total_drip_pipes_in_plot IS NOT NULL
    AND sensor_pipe_position IS NOT NULL
    AND pipe_length_m IS NOT NULL
)
# v1.1 fix: v1.0 hardcoded bed_center_spacing_cm IS NOT NULL, which would falsely
# leave furrow-method farmers permanently unresolved (their bed_center_spacing_cm
# is genuinely NULL). Now checks the spacing field appropriate to the chosen method.
```

---

## Summary matrix

| Class | Count | Rules |
|---|:---:|---|
| `EVENT` | 3 | WB-001, WB-003, WB-004 |
| `SILENT_GUARD` | 1 | WB-005 |
| `ONCE_UNTIL_RESOLVED` | 3 | WB-002, WB-006, WB-008 |
| `WINDOW` | 1 | WB-007 |

**Total: 8 rules — all delivery-class tagged.**

---

## Backend implementation note

Add `delivery_class` and `resolution_condition_dsl` (where applicable) to each rule's JSON body in `Domain3_Rules_Ginger.json`. Backend rule-runner honors these tags — no farmer-messaging engine changes required beyond standard delivery-class dispatch.

---

*End of D03-WB Delivery Class Tagging v1.0*
