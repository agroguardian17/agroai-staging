# Backend note — KB 7 Final Decisions integrated

**Date:** 1 October 2026
**From:** Backend
**To:** Kuldip — Agronomy Compliance Owner
**Ref:** `KB_7_FINAL_DECISIONS_RESPONSE.md` (30 Sep, 21:00 IST)
**PR:** agroguardian17/agroai-staging #101

All 7 received. Items 2, 3, 6, 7 recorded as keep-deployed confirmations — no code change; your Season-2 specs (D04-NS-003 ledger, D08-WD-002 registry, D03-WL-004 probe) stay reserved. Items **1, 4, 5** are wired in PR #101. Three things need your eyes.

## 1. Two rule-id collisions (resolved the usual way)

- **Item 4 — your `D06-BW-002` (and `D06-BW-003`) are already taken.** `D06-BW-002` is a live *nematode → wilt-risk* rule and `D06-BW-003` is an *aromatic-residue* rule. So the wilt-history prompt is authored as the next free id, **`D06-BW-004`** — otherwise identical to your spec (yellow, `ONCE_UNTIL_RESOLVED`, `plot_status == 'pre_planting' AND field_history_wilt IS NULL`, `SEQUENCES D06-BW-001`, your Marathi template).
- **Item 1 — `D04-MC-005` was free** (as you named it) ✅. Zone confirmed: the mapper already emits `marathwada_central` for the Kannad cluster, so the trigger fires exactly where intended.

## 2. Item 5 — the D03-MN list you asked for, and a correction on D03-MN-004

You asked for the full live `D03-MN-*` set and which read `soil_moisture_vwc` / `sub_node_moisture_status`:

| Rule | Severity | Deployed trigger | Reads VWC? |
|---|---|---|---|
| D03-MN-001 | info | `rainfall_mm > 2 AND dap BETWEEN 0 AND 225` | ❌ rainfall |
| **D03-MN-002** | red | `soil_moisture_vwc >= vwc_saturation` | ✅ **yes** |
| D03-MN-003 | yellow | `rain_gap_days >= 10 AND STAGE IN [G1,G2]` | ❌ rain-gap |
| **D03-MN-004** | red | `rain_gap_days >= 7 AND STAGE IN [G3,G4]` | ❌ **rain-gap, not VWC** |

- Only **D03-MN-002** reads `soil_moisture_vwc`. **No rule reads `sub_node_moisture_status`** (that field doesn't exist in the deployed KB).
- **D03-MN-004 is a forecast rain-gap dry-spell alert, not a VWC rule** — it doesn't depend on the sub-node battery. By your own criterion ("rules that don't read the VWC field aren't affected by battery-low state"), it shouldn't be suppressed: silencing it would kill a dry-spell red alert during a battery-upgrade window, when the forecast is still perfectly good.

**So I wired only `D03-SB-004 SUPPRESSES D03-MN-002` and held the D03-MN-004 edge.** Please confirm: given D03-MN-004 is rain-gap-driven (not VWC), do you still want it suppressed during the upgrade window, or leave it live? If you want it held live (my recommendation), item 5 is complete as shipped.

## 3. ZnSO₄ — base rule shipped; partial-dose tier deferred

Your D04-MC-005 spec had a three-tier resolution (≥9 kg resolved / 5–8 kg WARNING top-up / <5 or NULL unresolved). I shipped the **base rule** (fires while `basal_znso4_applied_kg_acre IS NULL`, silent once recorded). The **5–8 kg partial-dose WARNING** tier isn't wired yet, because it only becomes meaningful once the applied dose is captured (farmer/ops data that lands with the app). When that capture exists I'll add the top-up nudge as a companion rule. Flag if you'd rather it be a separate reserved id now.

## Also
`plot_status` (pre_planting / growing / post_harvest) is **derived by the backend from the season's sowing/harvest dates** — no farmer input needed — so both pre-planting prompts fire at the right phase.

Gates green (296 rules / 723 golden tests). Once you confirm item-5's D03-MN-004, the KB is closed for Season 1 on the buildable side.

— Backend
