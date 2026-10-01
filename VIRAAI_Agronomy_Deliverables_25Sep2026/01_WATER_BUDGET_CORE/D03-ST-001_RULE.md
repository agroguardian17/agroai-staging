# D03-ST-001 — Water Deficit Stress Log (silent guard rule)

**Purpose:** D11 yield model's factor-7 (drought during rhizome fill G3-G4) consumer rule. Silent — logs daily water-deficit ratio, no farmer message. Backend flagged as missing from loaded KB; this is the authoritative spec.

**Version:** 1.0
**Date:** 25 September 2026
**Author:** Kuldip — Agronomy Compliance Owner
**Domain:** D03 Water & Irrigation
**Category:** Stress log (silent, D11-consumer)

---

## Rule anatomy

### Identification
- **Rule ID:** `D03-ST-001`
- **Rule name:** water_deficit_stress_daily_log
- **Rule type:** SILENT_GUARD (no farmer notification; emits derived field for D11)
- **Compliance tag:** `COMPLIANT` (FAO-56 water balance methodology, VNMKV OFT indicative L3 basis)

### Trigger
```
DAP > 60                                          -- past establishment
AND flow_telemetry_present = TRUE                 -- hardware live
AND water_budget_confidence >= 0.60               -- reliable inputs
AND stage_water_target_L_per_plant IS NOT NULL    -- variety-stage target loaded
```

### Action
```
emit water_deficit_ratio = 1 - min(
    1.0,
    per_plant_water_stage_cumulative_L 
    ÷ stage_water_target_L_per_plant
)

emit stress_flag_today = (water_deficit_ratio >= 0.30)

update stress_days_running_count:
    IF stress_flag_today THEN increment BY 1
    ELSE reset TO 0

log to farm_brain.d11_factor7_queue:
    {plot_id, dap, stage, water_deficit_ratio, stress_flag_today, stress_days_running_count, timestamp}
```

### Severity
- `INFO` (silent — no farmer message, no WhatsApp push)
- Consumed by D11 yield model in nightly aggregation

### D11 wiring
- Feeds D11 factor-7 (drought during G3-G4 rhizome fill) — replaces old qualitative `I_i = stress_days / 30` with quantitative:
  ```
  I_i = 1 - min(1, per_plant_water_stage_cumulative_L / stage_water_target_L_per_plant)
  ```
- Aggregation window: G3-G4 (DAP 90-210) sum of daily `water_deficit_ratio`, mean-weighted

### Basis
- **L3 — VNMKV OFT indicative:** Stage-band water demand from AICRP-Spices ginger trials at VNMKV Parbhani
- **L2 — FAO-56 methodology:** Water balance (`ETc - effective_rainfall - irrigation`) as reference method for deficit computation
- **L3 — Marathwada context:** Kannad Western Scarcity zone — G3-G4 window overlaps late monsoon withdrawal; drought stress here has documented 15-25% yield impact per VNMKV records

### Kannad-specific note (kannad_note)
Western Scarcity zone, TMI < 40%. Peak rhizome-fill window (G3 90-150 DAP) starts ~mid-September, ends ~mid-November — overlapping late monsoon withdrawal. This rule captures precisely the DAP window where drought hits hardest for Kannad plots.

### Marathi note
पाण्याच्या तुटीचा दैनिक log — शेतकऱ्याला कोणताही message जात नाही. उत्पादन-अंदाज मॉडेल (D11) ला हा data feed होतो, ज्यामुळे हंगामाच्या शेवटी उत्पादन-अंदाज अधिक अचूक होतो. गड्डा-निर्मितीच्या (G3-G4) अवस्थेत तुटीचा effect सर्वाधिक असतो.

### Tests (golden — 5 required)
| Test | Input | Expected `water_deficit_ratio` |
|---|---|:---:|
| T1 | actual = target | 0.00 |
| T2 | actual = 0 | 1.00 |
| T3 | actual = target × 0.50 | 0.50 |
| T4 | actual = target × 1.20 (over-irrigation) | 0.00 (clamped) |
| T5 | `water_budget_confidence = 0.40` | rule silent (does not fire — no emit) |

### Precedence relations (D11 domain)
- `D03-ST-001 FEEDS D11-YM-007` (factor-7 consumer relationship — data emit, not conflict)
- No SUPPRESSES / SUPERSEDES / BUNDLES with any farmer-facing rule (silent by design)

### Confidence
- Emitted `water_deficit_ratio` inherits `water_budget_confidence` from §2.5 pinned formula
- If confidence drops < 0.60 mid-stage, rule pauses emission but keeps `stress_days_running_count` frozen (does not reset on confidence gap — resumes when confidence recovers)

---

## Backend implementation ask

- Add rule to `Domain3_Rules_Ginger.json` under `_rules[]`
- Wire consumer at D11 factor-7 aggregation cron (nightly 23:00 IST)
- No new schema fields — reuses `per_plant_water_stage_cumulative_L`, `stage_water_target_L_per_plant`, `water_budget_confidence` from §2.4 of Water Budget doc v1.3

**Estimated backend integration effort: 2 hours** (rule declaration + D11 consumer wiring + 5 golden tests).

---

*End of D03-ST-001 rule specification*
