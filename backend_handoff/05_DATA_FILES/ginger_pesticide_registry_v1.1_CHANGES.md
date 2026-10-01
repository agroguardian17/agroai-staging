# Ginger Pesticide Registry v1.1 — Change Log

**Date:** 2026-09-23
**Basis:** VNMKV Compliance Certificate VNMKV/AGRON/PP/AGROMET/2026-27/COMP/VIRAAI-001
**Supersedes:** v1.0 (2026-09-23 08:00 IST)

## Applied changes (6 entries updated)

| # | Molecule | v1.0 status | v1.1 status | Change |
|:---:|---|:---:|:---:|---|
| 1 | 🚨 **streptocycline** | CONDITIONAL | **CONFIRMED_BLOCKLIST** | Union Ministry gazette 1 Jan 2024 — WHO CIA, AMR prevention. **REGULATORY** |
| 2 | mancozeb | PROVISIONAL, PHI 7 | CONFIRMED_via_VNMKV, PHI 15-21 | VNMKV PHI correction |
| 3 | copper_oxychloride | PROVISIONAL, PHI 5 | CONFIRMED_via_VNMKV, PHI 15 | VNMKV PHI correction |
| 4 | metalaxyl_M | PROVISIONAL, PHI 21 | CONFIRMED_via_VNMKV, PHI 30 | VNMKV PHI correction + pre-mix preference |
| 5 | carbendazim | PROVISIONAL | CONFIRMED_via_VNMKV_RESTRICTED | SEED TREATMENT ONLY; late foliar/drench blocked |
| 6 | imidacloprid | PROVISIONAL, PHI 40 | CONFIRMED_via_VNMKV, PHI 30-40 | Clarified range |

## Statistics — v1.1

| Status | Count |
|---|:---:|
| CONFIRMED (biologicals, sulphur, neem) | 5 |
| CONFIRMED_via_VNMKV (mancozeb, COC, metalaxyl-M, imidacloprid) | 4 |
| CONFIRMED_via_VNMKV_RESTRICTED (carbendazim) | 1 |
| CONFIRMED_BLOCKLIST (**9 entries** — includes new streptocycline) | 9 |
| **Total** | **19** |

## Backend action

Load `ginger_pesticide_registry_v1.1.csv` into `_PHI_DAYS_BY_GROUP` map + blocklist gate.
Blocklist gate now catches 9 molecules (was 8) — streptocycline added.
Deprecate v1.0 immediately.

## Provenance note

- Streptocycline ban: published regulatory fact (Union Ministry gazette 2024-01-01) — apply immediately without VNMKV signature dependency
- PHI/dose corrections: reflect VNMKV extension bulletin consensus values; carry `CONFIRMED_via_VNMKV` pending physical signature on Compliance Certificate
- All entries meet the standing rule: "Blocklisted inputs must trigger a policy gate, not a value calculation"
