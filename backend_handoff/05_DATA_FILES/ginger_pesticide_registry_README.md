# Ginger Pesticide Registry — CIB&RC + FSSAI aligned

**File:** `ginger_pesticide_registry.csv`
**Date:** 2026-09-23
**Owner:** Kuldip — Agronomy Compliance Owner
**Total entries:** 19 · Registered: 10 · Conditional: 1 · Blocklist: 8

## Purpose

Single source of truth for the mapper's `_PHI_DAYS_BY_GROUP` map and the
blocklist gate that runs before PHI calculation (see D05-CH-008 and the
AGRONOMY_SIGNOFF §5 blocklist gate pattern).

## Source hierarchy

Each row's `source_ref` points to the primary regulatory or scientific
source. Precedence in evidence:
1. CIB&RC official label / registered-crops list (Central Insecticides Board)
2. FSSAI MRL gazette notifications
3. MoEF & Climate Change gazette (bans)
4. Stockholm Convention listings (POPs)
5. ICAR-IISR / VNMKV recommendation (for biologicals)
6. D05-CH-001 / D08-WD-001 immutable KB rules (internal cross-reference)

## Verification status

| Status | Meaning | Count |
|---|---|---:|
| `CONFIRMED` | Regulatory verified + agronomy confirmed | 5 |
| `CONFIRMED_BLOCKLIST` | Ban / non-registration verified from primary source | 8 |
| `PROVISIONAL_pending_VNMKV_verification` | Widely-used, needs formal VNMKV plant-protection sign-off | 6 |

Provisional entries should be re-verified with VNMKV Parbhani Plant
Protection department before Season 1 pilot. Nothing prevents mapper use
today — the values are conservative and food-safety oriented.

## Backend integration

Mapper pseudocode (from AGRONOMY_SIGNOFF §5):

```python
IF pesticide_group IN blocklist_for_crop:
    phi_days_remaining   = NULL
    phi_blocklist_hit    = TRUE
    farmer_alert_type    = 'blocklisted_input_detected'
    blocklist_reason     = registry[group].blocklist_reason_if_any
    blocklist_source_ref = registry[group].source_ref
ELSE:
    phi_days_remaining   = registry[group].phi_days OR 21
```

## Compliance notes

- **Absolute prohibitions** (chlorpyriphos, monocrotophos, phorate,
  endosulfan, BHC/lindane, carbofuran, methyl parathion, glyphosate
  post-emergence): mapper must refuse PHI calculation and surface the
  block reason to the farmer.
- **Conditional entries** (streptocycline): permitted only for confirmed
  bacterial wilt; must be flagged as export-restricted.
- **Biological inputs** (Trichoderma, Pseudomonas, Bacillus, sulphur,
  neem oil): no PHI, no MRL — safe defaults.
- **Systemic chemicals near harvest**: enforce PHI in days; UI must
  show days-remaining, not a raw calendar date.

## Open items

- VNMKV Parbhani plant-protection formal sign-off on 8 PROVISIONAL entries
- FSSAI MRL cross-check for each entry against current gazette notifications
- Trade-names list expansion — currently exemplar brands only
- Regional dose variations (some entries have different labels in different states)
