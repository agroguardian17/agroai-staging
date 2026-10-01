# KB Decision Sheet — 7 items blocking the remaining rule work

**Date:** 30 September 2026
**From:** Backend
**To:** Kuldip — Agronomy Compliance Owner
**Re:** The last tail of KB rules. Everything else (48 firing-intent rules, 5 D06 disease rules, 9 water-budget rules + compute engine, `previous_stage` transition rule, the 3 data tables) is **built and deployed**. The 7 decisions below are all that stand between us and closing the KB.

**How to answer:** put your pick + any note in the **Decision** line under each item. Where you're happy with my recommendation, "agree" is enough. Nothing here needs runtime/field data — these are design choices only.

---

## 1. `agro_climatic_zone` vocabulary → unblocks D04-MC-005 (basal ZnSO₄)

**Blocking:** The ZnSO₄ rule keys on agro-climatic zone. The backend mapper emits the zone as one of **`marathwada_central` / `marathwada_western` / `marathwada_eastern`** (Kannad = `marathwada_central`). Your bundle wrote the trigger against **`western_scarcity`**, which the mapper will never emit — so if we wire it as-is the rule can never fire.

**Need from you:** the mapping from your zone concept to our emitted values. Concretely: for the ZnSO₄ basal rule, which of `marathwada_central / marathwada_western / marathwada_eastern` should it fire in? (For the pilot, Kannad = `marathwada_central`.)

**Recommend:** fire in `marathwada_central` (+ any others you name). Once you confirm, this is a same-day wire.

**Decision:** _______________________________________________

---

## 2. D04-NS-003 (nitrogen timing) — keep deployed, or switch to the cumulative-N ledger?

**Deployed now (live):** `dap > 80 AND n_applied_kg_per_acre IS NOT NULL` · red — a simple "late N applied" flag.

**Your redesign:** compare **cumulative N applied vs the variety N-ceiling** (`variety_n_ceiling` table — already seeded: Mahima 61 / Varada 55 / Nadia 52 kg N/acre) with a hard DAP-150 cutoff.

**Trade-off:** the redesign is better agronomy but needs two new tracked inputs (`n_applied_kg_per_acre_cumulative`, `n_proposed_kg_per_acre`) plus a small backend build. The deployed rule works today with data we already have.

**Recommend:** **keep the deployed trigger for Season 1**, schedule the ledger redesign for Season 2 (it needs the N-application capture flow anyway). Confirm, or tell me to build the ledger now.

**Decision:** _______________________________________________

---

## 3. D08-WD-001 (herbicide) — keep deployed gate, or switch to the positive-list registry?

**Deployed now (live):** `(emergence_started OR dap >= 15) AND herbicide_post_emergent_date IS NULL` · blocking — a timing gate.

**Your redesign:** gate the *proposed herbicide* against the **registered-herbicide registry** (`registered_herbicide_registry` — already seeded, 13 entries) so only registered products pass.

**Trade-off:** the registry gate is the right long-term control but needs a `proposed_herbicide_input` field (a farmer/ops choice at spray time) that doesn't exist yet. The deployed timing gate is live and useful.

**Recommend:** **keep the deployed gate now**; add the registry gate as a *second* rule once the proposed-input capture exists (they're complementary — timing + compliance). Confirm.

**Decision:** _______________________________________________

---

## 4. D06-BW-002 — author the NULL-bypass companion, or drop it?

**Context:** D06-BW-001 (bacterial-wilt history, `field_history_wilt IS TRUE AND years_since_last_wilt < 5`) is wired. You flagged a possible companion **D06-BW-002** to handle the case where wilt history is unknown/NULL (so a missing history doesn't silently bypass the warning).

**Need from you:** do you want it, and if so what should it say + at what severity? (e.g. "wilt history not recorded → advise caution / request field history", yellow?)

**Recommend:** author a low-severity **info/yellow** prompt that asks for the missing history rather than blocking. Give me the trigger intent + Marathi line and I'll wire it.

**Decision:** _______________________________________________

---

## 5. D03-SB-004 — which moisture rules should low-battery state suppress?

**Context:** You proposed that when the sub-node battery is low (readings unreliable), D03-SB-004 should **suppress the D03-MN moisture-advisory rules** to avoid advising irrigation off bad data. The precedence engine currently needs the suppressed rules named **explicitly** (no wildcards yet).

**Need from you:** the exact list of D03-MN rule IDs to suppress (e.g. `D03-MN-002`, `D03-MN-004`, …), or confirm "all D03-MN rules" and I'll build wildcard support.

**Recommend:** name the specific moisture rules (cleaner, no engine change). If the set is large or will grow, I'll add wildcard precedence instead — your call.

**Decision:** _______________________________________________

---

## 6. Soil vocabulary — stay on Season-1 vocab, or migrate to the 5-class scheme?

**Deployed now:** two fields — `soil_type` (`vertisol`, …) and `soil_texture_class` (`heavy` / `medium` / `light`). Several live rules (D02-LY-001, D08-LY-001, D03-DS-001) key on these.

**Your bundle assumed:** a single richer 5-class `soil_texture_class` (`vertisol / heavy_clay / clay_loam_heavy / sandy_loam / clay_loam`).

**Trade-off:** migrating touches **every** soil rule, its field declarations, and its golden tests — a large cross-cutting change. The current vocab covers the pilot's vertisol-heavy reality.

**Recommend:** **stay on the Season-1 vocab** (map your 5 classes onto `vertisol` / `heavy`). This also settles the richer-hardware versions of D03-DS-001 / D02-DR-004 / D02-ST-002 — they need no rework under the current vocab. Confirm, or tell me you want the 5-class migration.

**Decision:** _______________________________________________

---

## 7. D03-WL-003 (waterlogging) — pick one trigger

**Two candidates disagree:**
- **Deployed (live):** `MONTH IN [OCT, NOV] AND forecast_rain_48h_mm > 40` · red
- **Your bundle:** `vwc_saturation_days_running >= 3`

**Need from you:** pick one (or keep both as separate rules). The deployed one is forecast-driven and live; yours is probe-driven (needs a running-saturation-days derivation, a small build).

**Recommend:** **keep the deployed forecast trigger** as the primary red alert; if you want the probe-driven version too, I'll add it as a companion once we derive `vwc_saturation_days_running`. Confirm.

**Decision:** _______________________________________________

---

## What happens after you answer

- **Items 1, 4, 5** → I wire the rules (D04-MC-005, D06-BW-002, D03-SB-004) — small KB PRs, each validated against the drift + golden-test gates.
- **Items 2, 3, 6, 7** → mostly "keep deployed" confirmations; any "build the redesign" answer becomes a scheduled backend+KB unit.
- Once these are in, the **KB and DB are complete** for Season 1 — the only remaining activation is runtime data capture (farmer/ops), which we're handling separately.

**Turnaround:** answers to 1/4/5 unblock ~2 days of KB work; 2/3/6/7 are confirmations.
