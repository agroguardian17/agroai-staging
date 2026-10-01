# Plant Density Sanity Thresholds

**Purpose:** Backend flags anomalies when `plot_plants_estimated` falls outside expected range for the given planting method. Catches farmer data-entry errors before they poison water-budget dose calculations.

**Version:** 1.0
**Date:** 25 September 2026
**Owner:** Kuldip — Agronomy Compliance Owner

---

## 1. Expected density ranges (VNMKV-standard for ginger, Marathwada)

| Planting method | Plants per acre (typical) | Plants per hectare (typical) | Notes |
|---|:---:|:---:|---|
| **Broad bed (recommended)** | 22,000 – 27,000 | 55,000 – 67,000 | 90 cm bed + 60 cm furrow, 22-25 cm plant spacing, 2 rows/bed |
| **Raised bed** | 30,000 – 36,000 | 74,000 – 89,000 | 60 cm bed + 60 cm furrow, 22-25 cm plant spacing, 2 rows/bed |
| **Furrow (traditional)** | 40,000 – 45,000 | 99,000 – 111,000 | 45 cm row spacing, 22-25 cm plant spacing |
| **Flat (NOT recommended on vertisol)** | 40,000 – 45,000 | 99,000 – 111,000 | Same as furrow; D02-LY-001 raises vnmkv_compliance_flag |

**Source tier:** L3 (VNMKV Package of Practices for ginger — Marathwada region)

---

## 2. Anomaly thresholds — backend action

Backend computes `plot_plants_estimated` per §2.1 formula (Water Budget doc v1.3). Compare against the range for the plot's `planting_method`:

| Deviation from typical range | Backend action |
|---|---|
| Within ±30% of typical | ✅ Accept; no flag |
| ±30% to ±50% | ⚠️ Warning flag; recommend farmer verify geometry; water-budget dose emitted with `dose_confidence_note = 'density_variance_moderate'` |
| Beyond ±50% | ❌ Reject; `plot_plants_estimated = NULL`; block dose recommendation; farmer prompt to re-enter planting geometry; log to agronomist review queue |

**Example thresholds (broad bed):**
- Typical: 22,000 – 27,000 plants/acre
- Warning band: 15,400 – 22,000 (low) or 27,000 – 35,100 (high)
- Reject band: < 15,400 or > 35,100

---

## 3. Additional sanity checks

### 3.1 Plot area sanity
| Check | Threshold | Action |
|---|---|---|
| `plot_area_m2` < 100 | Too small (likely bad polygon) | Reject; farmer re-capture prompt |
| `plot_area_m2` > 40,000 (10 acres) | Very large single plot for ginger | Warning; agronomist review; likely multiple plots merged |

### 3.2 Geometry consistency
| Check | Threshold | Action |
|---|---|---|
| `plant_spacing_within_row_cm` < 15 | Too dense — physically unlikely | Reject; farmer re-enter |
| `plant_spacing_within_row_cm` > 35 | Too sparse — inefficient | Warning; confirm with farmer |
| `bed_center_spacing_cm` < 60 (bed methods) | Below minimum for machinery | Warning; confirm |
| `bed_center_spacing_cm` > 200 | Unusually wide — verify | Warning |
| `rows_per_bed` = 1 on broad-bed | Underused bed | Warning; confirm intent (may be intentional in tight zones) |
| `rows_per_bed` > 3 on broad-bed | Overcrowded | Reject; VNMKV standard is 2 rows on 90 cm bed |

### 3.3 Dripper spacing sanity
| Check | Threshold | Action |
|---|---|---|
| `dripper_spacing_cm` < 20 | Too close — expensive drip system, unusual for ginger | Warning; confirm |
| `dripper_spacing_cm` > 45 | Too sparse — coverage gaps between plants | Warning; recommend 30 cm standard |

### 3.4 Pipe length sanity
| Check | Threshold | Action |
|---|---|---|
| `pipe_length_m` < 5 | Suspiciously short | Warning; confirm |
| `pipe_length_m` > 120 | Long lateral — pressure-loss risk end-of-line; sensor-position bias more important | Warning; recommend `sensor_pipe_position` capture |
| `total_drip_pipes × pipe_length_m > 3 × plot_perimeter_m` | Pipe-length total wildly exceeds plot perimeter × 3 (rough sanity for meander) | Warning; likely mis-entered |

---

## 4. Kannad-specific defaults (when farmer skips a field)

If farmer leaves a planting-geometry field blank at plot setup, use these Kannad-region defaults (VNMKV Package of Practices):

| Field | Kannad default |
|---|:---:|
| `planting_method` | broad_bed (recommended for vertisol) |
| `bed_height_cm` | 20 |
| `bed_width_cm` | 90 |
| `bed_center_spacing_cm` | 150 (90 bed + 60 furrow) |
| `plant_spacing_within_row_cm` | 22 |
| `rows_per_bed` | 2 |
| `furrow_center_spacing_cm` | 45 (if furrow method) |
| `dripper_spacing_cm` | 30 |
| `sensor_pipe_position` | unknown (farmer prompt to specify; confidence 0.80 until entered) |

Backend applies defaults only after farmer app displays them and farmer taps "OK, use defaults" — never silently.

---

## 5. Backend integration notes

- Add `plant_density_sanity_check()` function to farm_brain pipeline
- Run on every geometry change (farmer edit) and on daily 05:00 cron
- Log all warnings to `agronomist_review_queue` with `severity` enum: `info` / `warning` / `reject`
- Agronomist weekly digest surfaces the top 10 warning plots for follow-up

---

*End of Plant Density Sanity Thresholds v1.0*
