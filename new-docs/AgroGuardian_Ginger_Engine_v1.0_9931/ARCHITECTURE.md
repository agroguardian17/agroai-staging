# Agro-Guardian AI — Ginger Advisory Engine
## Architecture Documentation

**Version** 1.0 · **Date** 2 August 2026 · **Region** Kannad, Chhatrapati Sambhajinagar, Marathwada
**Status** Engine complete and gated. Zero field validation.

---

## 0. Read this first

Two things about this system are unusual and they shape every decision in it.

**It is a rule engine, not a learned model.** For the first two or three seasons there is no field data, 22 of 35 loss coefficients are author estimates, and there are no labelled images. Product material must describe it as *"a decision-support system running on agronomist-authored rules and sensor input, which becomes more accurate each season."* Five specific capability claims are prohibited and enforced in code — see §8.

**The value does not depend on machine learning.** Four decisions worth about ₹2.85 lakh per acre depend on doing something at the right time. Three of them cost nothing and the fourth costs about ₹6,000 in labour. A rule engine delivers those on day one.

---

## 1. What exists

```
431 rules across 13 domains
185 with machine-evaluable trigger expressions
434 golden tests
 44 reviewed by an agronomist panel
 16 immutable (cannot be overridden at runtime)
 39 typed precedence relations
306 Farm Brain fields
 19 database tables · 16 views
 15 blocking open items — all requiring field work or a phone call
```

Domain rule counts:

| | Domain | Rules | | Domain | Rules |
|---|---|---|---|---|---|
| D01 | Crop Lifecycle | 22 | D08 | Cultivation Operations | 38 |
| D02 | Soil & Land Prep | 27 | D09 | Harvest & Post-Harvest | 39 |
| D03 | Water & Irrigation | 31 | D10 | Institutional (schemes, contacts) | 35 |
| D04 | Nutrient & Fertiliser | 34 | D11 | Yield Impact (method) | 34 |
| D05 | Pest Management | 33 | D12 | AI Requirements (product policy) | 36 |
| D06 | Disease Management | 28 | D13 | Seed & Input Economics | 39 |
| D07 | Weather & Climate | 35 | | | |

---

## 2. Pipeline

Every advisory passes through six stages in this order. Skipping or reordering any of them reintroduces a bug that was already found and fixed.

```
Farm Brain state (sensors + records + plot facts)
        │
        ▼
  1. TRIGGER EVALUATION      trigger_dsl.py
     Three-valued logic. UNKNOWN never fires and is never read as FALSE.
        │
        ▼
  2. EXPERT OVERRIDES        expert_override.py
     Narrowest scope wins: plot > cluster > global. 16 rules refuse all overrides.
        │
        ▼
  3. PRECEDENCE              precedence.py
     Typed relations, not severity ranking. See §4 for why this matters.
        │
        ▼
  4. NOTIFICATION POLICY     notification_policy.py
     A condition stays true; the advice is an event. See §5.
        │
        ▼
  5. MESSAGE COMPOSITION     runner.py
     Four parts in Marathi: what, when, why, what if not.
        │
        ▼
  6. PERSISTENCE             persistence.py
     State survives restarts. Without this the daily job replays everything.
```

---

## 3. Three-valued logic

**The rule:** a field being absent is not the same as it being false.

```python
calibration_done unknown  →  UNKNOWN,  not FALSE
```

An UNKNOWN trigger does not fire, and the engine reports which field is missing. In Boolean logic a missing sensor reading silently becomes `false` and the alert is suppressed with no trace. Domain 12 `D12-COLD-001` requires the engine to degrade and say so — that requirement is only implementable with three-valued logic.

`Result.why()` names the missing field: `"insufficient data: current_stage"`.

### DSL grammar

```
expr       := or_expr
or_expr    := and_expr ( "OR" and_expr )*
and_expr   := not_expr ( "AND" not_expr )*
not_expr   := "NOT" not_expr | primary
primary    := "(" expr ")" | comparison
comparison := field op value
            | field "IN" "[" value, ... "]"
            | field "BETWEEN" value "AND" value
            | field "IS" ("NULL" | "NOT" "NULL" | "TRUE" | "FALSE")
            | "DURATION" "(" field ">" value ")" ">" n unit
            | "WITHIN" "(" date_field "," n unit ")"
            | "MONTH" "IN" "[" month, ... "]"
            | "STAGE" "IN" "[" stage, ... "]"
```

Field names resolve against `kb_farm_brain_fields`. **An undeclared name is a parse error, never a silent false.** This caught five invented field names during development.

`DURATION` exists because saturation damage is time-dependent, not level-dependent. Twelve hours of standing water is the trigger; an instantaneous reading is not.

---

## 4. Precedence — why severity ranking is wrong

The case that forced this design, taken from the knowledge base:

```
D04-MC-001  yellow  "spray micronutrients"     (45-60 DAP)
D04-MC-004  info    "above 35 C, postpone"
```

Ranked by severity the spray wins and the leaves scorch at 40 °C. `D04-MC-004` is not a competing instruction — it is a **condition on** another instruction, and ranking cannot express that.

So relations are typed:

| Relation | Meaning | Count |
|---|---|---|
| `SUPPRESSES` | B stops A being issued at all | 21 |
| `SUPERSEDES` | B replaces A; only B is shown | 9 |
| `BUNDLES` | A and B travel in one field visit | 5 |
| `SEQUENCES` | A must be answered before B is evaluated | 4 |
| `ESCALATES` | B raises A's severity; **one message, not two** | 3 |

Where no typed relation exists the fallback is severity, then priority, then u_value — **and the engine records that a fallback was used.** An unrecorded fallback is how the spray case slips back in.

`v_unguarded_instructions` lists instruction/blocker pairs sharing fields with no declared relation. It is a review queue, not an error list.

### Double counting

Thirteen factors appear in more than one domain — the cyclone alert in three, the mulch programme in three, the pre-harvest interval in three. Rules are written per domain but the yield computation is global.

```
raw u-value rules      : 71
after deduplication    : 56  (11 grouped + 45 ungrouped)
double counting avoided: 15 rules
```

Summing `kb_rules.u_value` directly counts the cyclone three times and makes every prediction pessimistic. Use `v_u_values_deduplicated`.

Where factors share a **causal chain** rather than a trigger — pest wound → rot, or FYM → weeds → weeding injury → rot — group them and apply the terminal u-value once.

---

## 5. Notification policy — a condition is not an event

The season simulation issued **998 messages across 301 days**, on every single day, with two blocking rules repeating 301 and 226 times.

The cause was a category error. A trigger expresses a **condition** and a condition stays true for as long as it is true. "Water supply is short" is true every day from April until it is fixed. But the **advice** is an event.

Four delivery classes:

| Class | Behaviour | Count |
|---|---|---|
| `SILENT_GUARD` | **No message unless the prohibited action is attempted.** Also used for internal computations. | 62 |
| `EVENT` | Rising edge only; re-armed once the condition clears | 53 |
| `WINDOW` | Advance warning, the day, then 3 overdue reminders | 38 |
| `ONCE_UNTIL_RESOLVED` | Once, then a 7/21/45/90-day ladder with rising severity | 32 |

`SILENT_GUARD` is the important one. 226 of the daily messages came from a rule that exists to stop a herbicide, firing on days nobody was spraying.

```
998 → 130 messages, no critical stage silent for more than 15 days
```

---

## 6. Multi-diagnosis

The Domain 6 differential returns one answer. Reality does not — rot and heat scorch can both be present.

```
CONFIRMED    decisive marker present    → treatment_rule returned
PROBABLE     one cause clearly ahead    → name the confirming test, no treatment
AMBIGUOUS    two or more within 0.15    → say which test separates them
NO_CANDIDATE insufficient observation   → ask, never guess
```

**`treatment_rule` is returned only on `CONFIRMED`.** That gate is tested. Domain 12 `D12-CLS-001` ("diagnosis before treatment") is now in code, not just in prose.

Weights are author estimates (`EST`) and must be corrected from first-season outcomes.

---

## 7. Expert override

An agronomist looking at a live plot in August cannot edit JSON and wait for a deploy. This is the runtime path.

**Kinds:** `THRESHOLD` · `DELIVERY` · `SEVERITY` · `DISABLE` · `PARAMETER`
**Scopes:** `plot` > `cluster` > `global` (narrowest wins)
**Expiry:** default 240 days, maximum 400

Guards, all tested:

- rationale under 15 characters → refused
- expiry over 400 days → refused (*"a permanent change belongs in the knowledge base"*)
- `blocking` rule disabled globally → refused; restrict to plot or cluster
- `blocking` severity lowered → refused; **use `DISABLE` so the record stays explicit**
- threshold value not present in the actual expression → refused
- threshold change on a `red`/`blocking` rule with a short rationale → refused

**Refused attempts are logged, not discarded.** An attempt to override an immutable rule is a governance signal.

### The immutable core (16 rules)

Enforced twice: by the API code path, and again by a PostgreSQL trigger in case the application layer is bypassed.

| Reason | Rules |
|---|---|
| Banned molecules | `D05-CH-001` |
| No fungicide for bacterial wilt | `D06-CH-001` `D06-DX-002` |
| Pre-harvest intervals | `D05-CH-003` `D06-CH-003` `D09-SF-002` |
| Caustic processing safety | `D09-SF-001` `D09-PR-001` `D09-PR-002` |
| DPDP consent and coordinates | `D12-DPDP-001` `D12-DPDP-002` `D12-DPDP-003` |
| Honest capability claims | `D12-POS-001` `D12-POS-003` |
| Brand independence | `D08-GR-003` |
| No profit guarantee | `D13-AD-002` |

An expert who disagrees escalates to a knowledge base revision with a written rationale — a slower process, on purpose.

---

## 8. Prohibited capability claims

Each traces to a finding in another domain, not to caution in the abstract.

| Claim | Why false |
|---|---|
| "the AI tells the farmer what to do" | It is a rule engine |
| "AI-driven yield prediction" | 22 of 35 coefficients are estimates |
| "machine learning optimises the crop" | No learned model exists |
| **"the NPK probe measures NPK"** | It measures EC; on calcareous soil CaCO₃ dominates |
| "we forecast the weather" | That is IMD's work; we correct and translate |

Enforced by `D12-POS-001` and `D12-POS-003`, both immutable.

---

## 9. Persistence — a production bug

Found by running the runner the way it will actually be deployed: as a scheduled job, so every run is a fresh process.

```
one long-lived process   :  5 messages / 5 days
a fresh process each day : 20 messages / 5 days — the same four rules daily
```

The 998→130 improvement is real only while the process stays up. Four things must persist:

- **notifier ladders** — else every standing advisory repeats daily
- **EVENT edges** — else the saturation alert repeats daily
- **overrides** — else the expert's change lasts one process
- **answered diagnostics** — else the same question repeats daily

Two safeguards: a **version mismatch** resets cleanly and reports why rather than half-restoring; a **run gap** is recorded so the caller can say the engine was down rather than silently replaying the whole ladder.

---

## 10. Database schema

### Knowledge base (generated — do not edit)

| Table | Holds |
|---|---|
| `kb_domains` | 13 domains, status, review dates |
| `kb_rules` | 431 rules, triggers, delivery class, immutable flag |
| `kb_rule_categories` | 151 categories, FK target from `kb_rules` |
| `kb_farm_brain_fields` | 306 fields — **the FK that prevents schema drift** |
| `kb_rule_fields` | rule → field links |
| `kb_rule_dependencies` | cross-domain feeds_into / depends_on |
| `kb_rule_references` | source citations per rule |
| `kb_golden_tests` | 434 test cases as JSONB |
| `kb_precedence` | 39 typed relations |
| `kb_duplication_groups` / `kb_duplication_members` | count-once enforcement |
| `kb_open_items` | 109 items, 15 blocking |
| `kb_stages` `kb_source_tiers` `kb_source_classes` | reference data |

### Runtime (written by the engine)

| Table | Holds |
|---|---|
| `engine_state` | notifier ladders, event edges, answered set, live overrides |
| `advisory_log` | what was issued, and `acted_on` for compliance |
| `kb_overrides` | expert overrides, scoped and expiring |
| `kb_override_audit` | CREATED / REVOKED / **REFUSED** / APPLIED |

### Key views

| View | Use |
|---|---|
| `v_u_values_deduplicated` | **Always use instead of summing `u_value`** |
| `v_rules_by_stage` | "what is due at DAP 82?" |
| `v_executable_rules` / `v_pending_triggers` | trigger coverage |
| `v_blocking` | everything that stops the engine |
| `v_immutable_rules` | the core that cannot move |
| `v_active_overrides` / `v_override_review` | override governance |
| `v_compliance` / `v_rule_effectiveness` | **the primary success metric** |
| `v_stale_plots` | daily job not running |
| `v_unguarded_instructions` | precedence review queue |
| `v_unintended_duplicate_actions` | expect 0 rows |

### Constraints that matter

```sql
rule_id_matches_domain     rule_id LIKE 'D' || lpad(domain_id) || '-%'
rule_no_filler_trigger     trigger_en !~* '\yrule +[0-9]+\y'
rule_kannad_note_filled    length(btrim(kannad_note)) > 20
kb_duplication_member_unique   a rule belongs to at most one group
no_self_relation           subject_rule <> object_rule
expiry_bounded             expires <= created + 400
trg_reject_immutable_override  DB-level refusal of immutable overrides
```

---

## 11. Build and test

```bash
python3 regression_gate.py       # must pass before regenerating
python3 json_to_sql.py --out agroguardian_ginger_kb.sql
psql -d agroguardian -f agroguardian_ginger_kb.sql
```

**The JSON files are the source of truth.** The SQL is a build artefact and carries a `DO NOT EDIT` header. To change a rule: edit the JSON, run the gate, regenerate.

### The gate

Five suites plus season-level assertions:

```
max_messages      200   notification fatigue
min_messages       40   engine gone quiet
max_per_day         6   flooding on one day
max_silence        21   days without advice in G1/G3/G4
max_repeat_share  25%   one rule dominating
diagnosis repeat    5   edge detection broken
```

**Every bound came from a real defect** — 998 messages, a 39-day G4 silence, one rot event diagnosed 206 times. Unit tests could see none of them.

---

## 11A. Which files actually run

Of the 35 files delivered, **seven run in production**. The rest are build-time
or test-time only.

```
RUNTIME  — 7 files, 119 KB

  trigger_dsl.py           parser and three-valued evaluator
  precedence.py            resolver + multi-diagnosis
  notification_policy.py   the four delivery behaviours
  expert_override.py       override API + refusal logic
  persistence.py           state across restarts
  runner.py                entry point and message composition
  runtime_loader.py        supplies rules and data from the database

DATA     — the knowledge base, as SQL

  agroguardian_ginger_kb.sql loaded into PostgreSQL
```

### Why runtime_loader.py exists

Four data sets exist **twice** — once in the build files, once in the knowledge base:

| Data | Build file | Knowledge base |
|---|---|---|
| 185 trigger expressions | `triggers_wave1/2/3.py` | `kb_rules.trigger_expr` |
| 152 delivery classes | `notification_policy.py` | `kb_rules.delivery` |
| 39 precedence relations | `precedence.py` | `kb_precedence` |
| 16 immutable rules | `expert_override.py` | `kb_rules.immutable` |

They agree today because the same converter wrote both. **They will not stay in
agreement**, because an expert amending a rule edits the JSON and regenerates
the SQL — the `.py` files are never touched.

So in production the engine reads the database. `runtime_loader.py` supplies
`JsonSource`, `PostgresSource` and `SqliteSource` behind one interface, and
`test_runtime_loader.py` fails the build the day the two sets diverge.

```python
from runtime_loader import PostgresSource, build_runner
from persistence import PersistentRunner, SqliteStateStore

pr = build_runner(PostgresSource(DSN), state_store=SqliteStateStore('engine.db'))
res = pr.run_day('PLOT-77', farm_brain_state, date.today(), cluster_id='KND-01')
```

The `triggers_wave*.py` files and the hard-coded maps inside the other modules
are **authoring surfaces**. They are how a human writes a rule. They are not how
the engine reads one.

### Everything else

| Purpose | Files |
|---|---|
| Build | `json_to_sql.py` `classify_decisions.py` `apply_review.py` |
| Authoring | `triggers_wave1.py` `triggers_wave2.py` `triggers_wave3.py` |
| Test | `regression_gate.py` and six suites |
| Development | `simulate_season.py` |

None ships to a server.

---

## 12. File manifest

### Engine (deploy these)

| File | Lines | Role |
|---|---|---|
| `trigger_dsl.py` | 400 | Parser and three-valued evaluator |
| `precedence.py` | 480 | Typed relations + multi-diagnosis |
| `notification_policy.py` | 230 | Four delivery classes |
| `expert_override.py` | 380 | Runtime overrides + immutable core |
| `persistence.py` | 300 | State across restarts (File + SQLite) |
| `runner.py` | 470 | **Single entry point.** Message composition |
| `triggers_wave1.py` | 640 | 55 triggers — all blocking/red |
| `triggers_wave2.py` | 520 | 59 triggers — the season's voice |
| `triggers_wave3.py` | 530 | 71 triggers — weather and water |
| `runtime_loader.py` | 260 | **Loads rules from the DB, not the build files** |

### Build tools

| File | Role |
|---|---|
| `json_to_sql.py` | Validates all 13 files, emits the SQL |
| `classify_decisions.py` | Assigns `decision_type` and `automation` |
| `apply_review.py` | Applies expert review, preserves superseded values |
| `simulate_season.py` | 240-day synthetic season, 5 scenarios |

### Tests

| File | Covers |
|---|---|
| `regression_gate.py` | **Run this.** All suites + season assertions |
| `run_trigger_tests.py` | 434 golden tests, field declaration, coverage |
| `test_precedence.py` | Relations + diagnosis gate |
| `test_override.py` | 16 immutable × 3 kinds = 48 refusals |
| `test_runner.py` | Message quality, engine-speak detection |
| `test_persistence.py` | Restart, expiry, revocation, round trip |
| `test_runtime_loader.py` | **Build-file vs knowledge-base drift** |

### Knowledge base (source of truth)

```
Domain1_Rules_Ginger_v2.json  ← use v2, not v1
Domain2..Domain13_Rules_Ginger.json
```

Each contains `_schema` (inherited from Domain 1), `metadata`, `reference_data`, `rules`, `open_items`, `summary`, `next_steps`, `author_note`, `legal`.

### Generated

```
agroguardian_ginger_kb.sql    1.13 MB — DO NOT EDIT
```

### Reference documents

```
T1_Expert_Review_Sheet.docx   46 rules routed to 4 reviewer types
```

---

## 13. Rule anatomy

```json
{
  "rule_id": "D08-EU-001",
  "category": "EU", "priority": 5, "severity": "yellow", "stage": "G3",
  "decision_type": "SCHEDULED_REMINDER", "automation": "assisted",
  "delivery": "WINDOW", "immutable": false,
  "status": "AGRONOMIST_REVIEWED",

  "trigger": {
    "english": "...", "marathi": "...",
    "expr": "dap BETWEEN 75 AND 90 AND earthing_up_date IS NULL AND flowering_observed IS FALSE",
    "expr_version": "dsl-1.0",
    "golden_tests": [ {"context": {...}, "expect": "TRUE", "label": "..."} ]
  },
  "action":    { "english": "...", "marathi": "..." },
  "reasoning": { "agronomic_basis": "...", "yield_impact": "...",
                 "confidence_score": 0.88, "source_tier": "A", "references": [...] },
  "cross_domain_dependencies": { "feeds_into": [...], "depends_on": [...] },
  "farm_brain_schema": ["earthing_up_date", "dap", ...],
  "u_value": 0.125, "recoverability": "none", "source_class": "SRC-Q",
  "kannad_note": "...",
  "review": { "tier": "T1", "outcome": "amended", "superseded": {...} }
}
```

`review.superseded` preserves the original author decision when an expert amends a rule, so the two can be compared after a season of field data.

---

## 14. Integration checklist

**Farm Brain state** must supply, per plot per day:

- sensor: `soil_moisture_vwc`, `soil_temp_c`, `saturation_hours`, `ec_current`
- station: `air_temp_max_c`, `rh_pct`, `rainfall_mm`, `pan_evaporation_mm_day`, `wind_speed_ms`
- derived: `<field>__duration` for any field used in `DURATION(...)`
- synthetic: `current_month`, `days_to_planting`, `days_to_harvest`
- records: operation dates, observations, plot facts

**Sampling frequency by stage** (power budget on the ATmega328P sub-node is finite): hourly in G1/G3/G4, four-hourly in G2/G5, daily in G0, hourly at all stages during a rain alert.

**Calling the engine:**

```python
from persistence import PersistentRunner, SqliteStateStore
pr = PersistentRunner(store=SqliteStateStore('engine.db'))
res = pr.run_day('PLOT-77', farm_brain_state, date.today(), cluster_id='KND-01')
for m in res['messages']:
    send(m.render())
```

`res` also carries `unknown` (what could not be decided and why), `gap_days`, `suppressed`, `held`, and `diagnosis`.

**Cluster alerts must be aggregate.** *"This area has raised disease pressure"* — never *"your neighbour's field has rot."* In a 5–10 farm cluster an aggregate statement may still identify the source, so wait until two or three farms show the condition.

---

## 15. What is not done

### Blocking — field work, not code

| Item | Owner | Unblocks |
|---|---|---|
| Ceiling: 94 or 113 q/acre | Kasbe Digraj (one phone call) | Domain 11 and 13 arithmetic |
| Drip capital cost | Supplier quotation | Both subsidy models |
| Two-point sensor calibration | Field, one day | **Automated irrigation** |
| Percolation pit test | Field, one day, zero cost | Drainage verdict |
| Seed rate reconciliation | Season 1 count | Largest cost line |
| DPDP consent structure | Legal advice | Data collection at scale |
| CIB&RC label claims | CIB&RC current list | Chemical dose confidence |

15 blocking items in total. **None is a code problem.**

### Known gaps

- **5 rules without triggers** — `D07-CL-001`, `D07-CC-002`, `D08-IC-002`, `D13-RP-001`, `D02-ST-001`. These are "when someone asks" rules with no condition. Correct as they are.
- **Satellite/NDVI is absent** from the knowledge base. The schema has the table; no rule uses it. Note that Domain 6 warns a partially infected crop stays green above ground while the rhizome is compromised — so whether NDVI detects rot *earlier* or *later* than the sensors must be tested, not assumed.
- **Fertiliser dosing is not sensor-driven.** The probe measures EC, not NPK. Doses come from the soil test. The probe's real use is fertigation verification: no EC rise within 2–4 hours means the fertiliser never reached the roots.
- **PostgreSQL adapter for `persistence.py`** — File and SQLite implementations exist; the interface is identical.
- **T3/T4 expert review** — 170 and 22 rules respectively, not yet reviewed. The 44 reviewed carry 100% of the u-value weight.

### Honest position

The system has never run on a real field. 22 of 35 loss coefficients are estimates. The agreement between the computed scenario (50 q/acre) and the Maharashtra state average (53 q/acre) is **one validation point and may be coincidence**.

**The first season is not a yield season. It is a validation season.** Domain 12 names ten minimum records; without them the season produces advice but no learning, and records cannot be reconstructed afterwards.

---

## 16. Success metric

Not messages sent. Not app opens. Not "AI accuracy".

```
action compliance rate = actions completed on time / actions issued
target season 1: >60%    target season 3: >80%
```

Four decisions worth ₹2.85 lakh/acre all depend on doing something at the right time. **System success is whether the farmer acted on time** — and measuring that needs a record, not a model. `v_rule_effectiveness` shows which rules are acted on and which are ignored; a high-u_value rule with low compliance is either badly worded or asking for something the farmer cannot do. Both are learnable and neither is visible without the log.
