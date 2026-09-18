#!/usr/bin/env python3
"""
AgroGuardian AI — Ginger Knowledge Base
JSON to PostgreSQL converter

Reads the thirteen domain rule files, validates them as a whole, and emits
one loadable SQL file.

The validation is the point. Each JSON file is internally consistent, but
several constraints only exist ACROSS files:
  - rule_id uniqueness is global
  - farm_brain fields declared in one domain are used in another
  - twelve duplication groups span multiple domains and must resolve
  - a u-value belonging to a duplication group must contribute once

Usage:  python3 json_to_sql.py [--out FILE] [--strict]
"""

import json, re, sys, argparse, hashlib
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CROP = "ginger"
SCHEMA_VERSION = "2.0"

DOMAIN_FILES = [
    ("Domain1_Rules_Ginger_v2.json", 1),
    ("Domain2_Rules_Ginger.json",    2),
    ("Domain3_Rules_Ginger.json",    3),
    ("Domain4_Rules_Ginger.json",    4),
    ("Domain5_Rules_Ginger.json",    5),
    ("Domain6_Rules_Ginger.json",    6),
    ("Domain7_Rules_Ginger.json",    7),
    ("Domain8_Rules_Ginger.json",    8),
    ("Domain9_Rules_Ginger.json",    9),
    ("Domain10_Rules_Ginger.json",  10),
    ("Domain11_Rules_Ginger.json",  11),
    ("Domain12_Rules_Ginger.json",  12),
    ("Domain13_Rules_Ginger.json",  13),
    ("Domain14_Rules_Ginger.json",  14),
]

DOMAIN_NAME_TO_ID = {
    "domain_1_lifecycle": 1, "domain_2_soil": 2, "domain_3_water": 3,
    "domain_4_nutrient": 4, "domain_5_pest": 5, "domain_6_disease": 6,
    "domain_7_weather": 7, "domain_8_operations": 8, "domain_9_harvest": 9,
    "domain_10_institutional": 10, "domain_11_yield": 11,
    "domain_12_ai": 12, "domain_13_economics": 13,
    "domain_14_satellite": 14,
}

FILLER_RE = re.compile(r"\brule\s+\d+\b", re.I)


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------

def q(v):
    """Quote a value for PostgreSQL. Handles None, numbers, bools, text."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v).replace("'", "''")
    return "'" + s + "'"


def arr(items):
    """PostgreSQL text array literal."""
    if not items:
        return "NULL"
    inner = ", ".join(q(str(i)) for i in items)
    return f"ARRAY[{inner}]::TEXT[]"


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_domains(base: Path):
    domains = []
    for fname, did in DOMAIN_FILES:
        p = base / fname
        if not p.exists():
            raise SystemExit(f"MISSING FILE: {fname}")
        with p.open(encoding="utf-8") as f:
            d = json.load(f)
        actual = d["metadata"]["domain"]
        if actual != did:
            raise SystemExit(f"{fname}: metadata.domain is {actual}, expected {did}")
        domains.append((did, fname, d))
    return domains


def collect_fields(domains):
    """Every farm_brain field declared anywhere, with the domain that declared it."""
    fields = {}
    for did, fname, d in domains:
        sch = d["_schema"]
        base = sch.get("farm_brain_fields", {})
        adds = sch.get("additions", {}).get("new_farm_brain_fields", {})
        for name, spec in list(base.items()) + list(adds.items()):
            if name not in fields:
                fields[name] = (spec, did)
    return fields


def collect_categories(domains):
    cats = {}
    for did, fname, d in domains:
        adds = d["_schema"].get("additions", {})
        key = f"rule_categories_domain_{did}"
        block = adds.get(key) or d["_schema"].get(f"rule_categories_domain_{did}") \
                or d["_schema"].get("rule_categories_domain_1", {})
        if did == 1 and not block:
            block = d["_schema"].get("rule_categories_domain_1", {})
        for code, desc in (block or {}).items():
            cats[(did, code)] = desc
    return cats


def collect_duplication_groups(domains):
    for did, fname, d in domains:
        pol = d["_schema"].get("additions", {}).get("double_counting_policy")
        if pol:
            return pol.get("known_duplications", []), pol.get("causal_chain_policy", "")
    return [], ""


# ---------------------------------------------------------------------------
# Validation — this is the reason the converter exists
# ---------------------------------------------------------------------------

def validate(domains, fields, cats, dupgroups):
    errors, warnings = [], []
    all_rules = {}
    action_hashes = defaultdict(list)

    for did, fname, d in domains:
        rules = d["rules"]

        declared = d["metadata"].get("total_rules")
        if declared != len(rules):
            errors.append(f"D{did:02d} metadata.total_rules={declared} but file has {len(rules)}")

        for r in rules:
            rid = r["rule_id"]

            if rid in all_rules:
                errors.append(f"DUPLICATE rule_id {rid} in D{did:02d} and D{all_rules[rid]:02d}")
            all_rules[rid] = did

            if not rid.startswith(f"D{did:02d}-"):
                errors.append(f"{rid}: prefix does not match domain {did}")

            if (did, r["category"]) not in cats:
                errors.append(f"{rid}: category '{r['category']}' not declared for D{did:02d}")

            c = r["reasoning"]["confidence_score"]
            if not (0.0 <= c <= 1.0):
                errors.append(f"{rid}: confidence_score {c} outside 0..1")

            if FILLER_RE.search(r["trigger"]["english"]):
                errors.append(f"{rid}: filler pattern in trigger")

            if len((r.get("kannad_note") or "").strip()) < 20:
                errors.append(f"{rid}: kannad_note too short or empty")

            if len(r["reasoning"]["agronomic_basis"].strip()) < 40:
                errors.append(f"{rid}: agronomic_basis too short")

            u = r.get("u_value")
            if u is not None and not (0.0 <= u <= 1.0):
                errors.append(f"{rid}: u_value {u} outside 0..1")

            for fld in r["farm_brain_schema"]:
                if fld not in fields:
                    errors.append(f"{rid}: undeclared farm_brain field '{fld}'")

            for direction in ("feeds_into", "depends_on"):
                for tgt in r["cross_domain_dependencies"].get(direction, []):
                    if tgt not in DOMAIN_NAME_TO_ID:
                        errors.append(f"{rid}: unknown dependency target '{tgt}'")

            h = hashlib.md5(r["action"]["english"].strip().encode()).hexdigest()
            action_hashes[h].append(rid)

    group_of = {rid: g["group"] for g in dupgroups for rid in g["rules"]}
    for h, rids in action_hashes.items():
        if len(rids) > 1:
            groups = {group_of.get(r) for r in rids}
            if len(groups) == 1 and None not in groups:
                warnings.append(
                    f"identical action text within declared group '{groups.pop()}': "
                    + ", ".join(rids) + "  (permitted — one advisory, several domains)")
            else:
                errors.append(
                    "IDENTICAL action text across rules NOT in one duplication group: "
                    + ", ".join(rids)
                    + "  -> either differentiate them or declare a duplication group")

    # duplication groups must resolve, and members should agree on u_value
    for g in dupgroups:
        for rid in g["rules"]:
            if rid not in all_rules:
                errors.append(f"duplication group '{g['group']}' references unknown rule {rid}")
        gu = g.get("u_value")
        if gu is not None:
            member_us = []
            for did, fname, d in domains:
                for r in d["rules"]:
                    if r["rule_id"] in g["rules"] and r.get("u_value") is not None:
                        member_us.append((r["rule_id"], r["u_value"]))
            off = [m for m in member_us if abs(m[1] - gu) > 0.001]
            if off:
                warnings.append(
                    f"group '{g['group']}' declares u={gu} but members differ: "
                    + ", ".join(f"{a}={b}" for a, b in off)
                    + "  (expected — the group value is authoritative)"
                )

    # any u-value carrying rule NOT in a group is counted independently
    grouped = {rid for g in dupgroups for rid in g["rules"]}
    ungrouped_u = []
    for did, fname, d in domains:
        for r in d["rules"]:
            if r.get("u_value") is not None and r["rule_id"] not in grouped:
                ungrouped_u.append((r["rule_id"], r["u_value"]))

    return errors, warnings, all_rules, ungrouped_u


# ---------------------------------------------------------------------------
# Emit
# ---------------------------------------------------------------------------

def emit(domains, fields, cats, dupgroups, chain_policy, out):
    w = out.write
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    w(f"""-- ============================================================================
-- AGRO-GUARDIAN AI  |  Ginger Knowledge Base
-- Generated by json_to_sql.py on {now}
--
-- Source        : {len(domains)} domain JSON files (schema v{SCHEMA_VERSION})
-- Crop          : {CROP}
-- Geography     : Kannad, Chhatrapati Sambhajinagar, Marathwada, Maharashtra
-- Units         : PER ACRE throughout
--
-- DO NOT EDIT THIS FILE. Edit the JSON and regenerate.
-- The JSON files are the source of truth; this is a build artefact.
--
-- What this file adds over the JSON: constraints that only hold ACROSS
-- domains. Rule id uniqueness, farm_brain field declaration, and the twelve
-- duplication groups are enforced here by the database rather than checked
-- by a script.
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Reference tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS kb_source_tiers (
    tier CHAR(1) PRIMARY KEY,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS kb_source_classes (
    source_class TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    production_allowed BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS kb_stages (
    stage_code TEXT PRIMARY KEY,
    name_en TEXT NOT NULL,
    name_mr TEXT NOT NULL,
    dap_start INT, dap_end INT,
    criticality TEXT CHECK (criticality IN ('low','medium','medium_high','high','highest')),
    critical_irrigation BOOLEAN DEFAULT FALSE,
    recoverable TEXT CHECK (recoverable IN ('none','partial','full'))
);

CREATE TABLE IF NOT EXISTS kb_domains (
    domain_id INT PRIMARY KEY,
    name_en TEXT NOT NULL,
    name_mr TEXT NOT NULL,
    crop TEXT NOT NULL DEFAULT 'ginger',
    source_document TEXT,
    version TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN
        ('PHASE_1_RAW_UNVALIDATED','AGRONOMIST_REVIEWED','FIELD_VALIDATED','PRODUCTION')),
    agronomist_validated BOOLEAN NOT NULL DEFAULT FALSE,
    total_rules INT NOT NULL,
    review_by DATE,
    purpose TEXT,
    central_finding TEXT,
    author_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON COLUMN kb_domains.review_by IS
 'Set only where content expires. Domains 9, 10 and 12 have dates; the agronomy domains do not.';

CREATE TABLE IF NOT EXISTS kb_farm_brain_fields (
    field_name TEXT PRIMARY KEY,
    spec TEXT NOT NULL,
    declared_in_domain INT NOT NULL REFERENCES kb_domains(domain_id)
);
COMMENT ON TABLE kb_farm_brain_fields IS
 'The shared vocabulary. The foreign key on kb_rule_fields is what makes drift between domains impossible.';

CREATE TABLE IF NOT EXISTS kb_rule_categories (
    domain_id INT NOT NULL REFERENCES kb_domains(domain_id),
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    PRIMARY KEY (domain_id, category)
);

-- ---------------------------------------------------------------------------
-- Rules
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS kb_rules (
    rule_id TEXT PRIMARY KEY,
    domain_id INT NOT NULL REFERENCES kb_domains(domain_id),
    category TEXT NOT NULL,
    priority INT NOT NULL CHECK (priority BETWEEN 1 AND 5),
    severity TEXT NOT NULL CHECK (severity IN ('info','yellow','red','blocking')),
    stage_code TEXT REFERENCES kb_stages(stage_code),

    trigger_en TEXT NOT NULL,
    trigger_mr TEXT NOT NULL,
    trigger_expr TEXT,
    trigger_expr_version TEXT,
    delivery TEXT CHECK (delivery IN ('ONCE_UNTIL_RESOLVED','EVENT','WINDOW','SILENT_GUARD')),
    immutable BOOLEAN NOT NULL DEFAULT FALSE,
    immutable_reason TEXT,
    action_en  TEXT NOT NULL,
    action_mr  TEXT NOT NULL,

    agronomic_basis TEXT NOT NULL,
    yield_impact TEXT,
    confidence_score NUMERIC(3,2) NOT NULL CHECK (confidence_score BETWEEN 0 AND 1),
    source_tier CHAR(1) NOT NULL REFERENCES kb_source_tiers(tier),
    source_class TEXT NOT NULL REFERENCES kb_source_classes(source_class),

    u_value NUMERIC(4,3) CHECK (u_value IS NULL OR u_value BETWEEN 0 AND 1),
    recoverability TEXT NOT NULL CHECK (recoverability IN ('none','partial','full')),
    kannad_note TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    FOREIGN KEY (domain_id, category) REFERENCES kb_rule_categories(domain_id, category),

    CONSTRAINT rule_id_matches_domain CHECK (rule_id LIKE 'D' || lpad(domain_id::text,2,'0') || '-%'),
    CONSTRAINT rule_no_filler_trigger  CHECK (trigger_en !~* '\\yrule +[0-9]+\\y'),
    CONSTRAINT rule_kannad_note_filled CHECK (length(btrim(kannad_note)) > 20),
    CONSTRAINT rule_basis_filled       CHECK (length(btrim(agronomic_basis)) > 40)
);
COMMENT ON CONSTRAINT rule_no_filler_trigger ON kb_rules IS
 'Blocks auto-generated placeholder rules of the form "X management rule 6".';
COMMENT ON CONSTRAINT rule_kannad_note_filled ON kb_rules IS
 'The region-specific slot must not be empty.';

-- Identical action text is legitimate where rules are declared as one factor,
-- so this is surfaced as a view rather than enforced as a unique index.
-- See v_unintended_duplicate_actions below.
CREATE INDEX IF NOT EXISTS kb_rules_domain   ON kb_rules (domain_id);
CREATE INDEX IF NOT EXISTS kb_rules_stage    ON kb_rules (stage_code);
CREATE INDEX IF NOT EXISTS kb_rules_severity ON kb_rules (severity);
CREATE INDEX IF NOT EXISTS kb_rules_uvalue   ON kb_rules (u_value) WHERE u_value IS NOT NULL;

COMMENT ON COLUMN kb_rules.delivery IS
 'How often the advice actually reaches the farmer. A condition stays true; the advice is an event. SILENT_GUARD rules produce no message unless the prohibited action is attempted.';
COMMENT ON COLUMN kb_rules.trigger_expr IS
 'Machine-evaluable DSL expression. Three-valued: an UNKNOWN result must not fire and must not be read as FALSE.';

CREATE TABLE IF NOT EXISTS kb_golden_tests (
    rule_id TEXT NOT NULL REFERENCES kb_rules(rule_id) ON DELETE CASCADE,
    seq INT NOT NULL,
    context JSONB NOT NULL,
    expect TEXT NOT NULL CHECK (expect IN ('TRUE','FALSE','UNKNOWN')),
    label TEXT,
    PRIMARY KEY (rule_id, seq)
);
COMMENT ON TABLE kb_golden_tests IS
 'Each trigger expression ships with the cases that prove it fires when it should and, more importantly, does not fire on the near miss.';

CREATE TABLE IF NOT EXISTS kb_rule_fields (
    rule_id TEXT NOT NULL REFERENCES kb_rules(rule_id) ON DELETE CASCADE,
    field_name TEXT NOT NULL REFERENCES kb_farm_brain_fields(field_name),
    PRIMARY KEY (rule_id, field_name)
);

CREATE TABLE IF NOT EXISTS kb_rule_references (
    rule_id TEXT NOT NULL REFERENCES kb_rules(rule_id) ON DELETE CASCADE,
    reference TEXT NOT NULL,
    PRIMARY KEY (rule_id, reference)
);

CREATE TABLE IF NOT EXISTS kb_rule_dependencies (
    rule_id TEXT NOT NULL REFERENCES kb_rules(rule_id) ON DELETE CASCADE,
    direction TEXT NOT NULL CHECK (direction IN ('feeds_into','depends_on')),
    target_domain_id INT NOT NULL REFERENCES kb_domains(domain_id),
    PRIMARY KEY (rule_id, direction, target_domain_id)
);

-- ---------------------------------------------------------------------------
-- Duplication groups — the constraint that cannot exist in separate files
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS kb_duplication_groups (
    group_name TEXT PRIMARY KEY,
    u_value NUMERIC(4,3) CHECK (u_value IS NULL OR u_value BETWEEN 0 AND 1),
    count_once BOOLEAN NOT NULL DEFAULT TRUE,
    note TEXT
);
COMMENT ON TABLE kb_duplication_groups IS
 'Rules are written per domain but the yield computation is global. A factor appearing in several domains must contribute its u-value exactly once.';

CREATE TABLE IF NOT EXISTS kb_duplication_members (
    group_name TEXT NOT NULL REFERENCES kb_duplication_groups(group_name) ON DELETE CASCADE,
    rule_id TEXT NOT NULL REFERENCES kb_rules(rule_id) ON DELETE CASCADE,
    PRIMARY KEY (group_name, rule_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS kb_duplication_member_unique ON kb_duplication_members (rule_id);
COMMENT ON INDEX kb_duplication_member_unique IS
 'A rule may belong to at most one duplication group, otherwise the count-once guarantee fails.';

CREATE TABLE IF NOT EXISTS kb_precedence (
    subject_rule TEXT NOT NULL REFERENCES kb_rules(rule_id) ON DELETE CASCADE,
    relation TEXT NOT NULL CHECK (relation IN
        ('SUPPRESSES','SUPERSEDES','ESCALATES','BUNDLES','SEQUENCES')),
    object_rule TEXT NOT NULL REFERENCES kb_rules(rule_id) ON DELETE CASCADE,
    reason_en TEXT NOT NULL,
    reason_mr TEXT NOT NULL,
    PRIMARY KEY (subject_rule, relation, object_rule),
    CONSTRAINT no_self_relation CHECK (subject_rule <> object_rule)
);
COMMENT ON TABLE kb_precedence IS
 'Typed relations between rules that can fire together. Severity ranking alone gives the wrong answer where one rule is a condition on another rather than a competing instruction.';

COMMENT ON COLUMN kb_rules.immutable IS
 'An expert cannot override this rule at runtime. Disagreement escalates to a knowledge base revision with a written rationale, which is a slower process on purpose.';

CREATE TABLE IF NOT EXISTS kb_overrides (
    override_id TEXT PRIMARY KEY,
    rule_id TEXT NOT NULL REFERENCES kb_rules(rule_id),
    kind TEXT NOT NULL CHECK (kind IN ('THRESHOLD','DELIVERY','SEVERITY','DISABLE','PARAMETER')),
    scope TEXT NOT NULL CHECK (scope IN ('plot','cluster','global')),
    scope_id TEXT,
    expert_id TEXT NOT NULL,
    expert_name TEXT NOT NULL,
    rationale_mr TEXT NOT NULL CHECK (length(btrim(rationale_mr)) >= 15),
    created DATE NOT NULL,
    expires DATE NOT NULL,
    payload JSONB,
    revoked DATE,
    revoked_by TEXT,
    applied_count INT NOT NULL DEFAULT 0,
    CONSTRAINT scope_needs_id CHECK (scope = 'global' OR scope_id IS NOT NULL),
    CONSTRAINT expiry_after_creation CHECK (expires > created),
    CONSTRAINT expiry_bounded CHECK (expires <= created + 400)
);
COMMENT ON TABLE kb_overrides IS
 'Runtime rule adjustment by an authorised expert. Every override is scoped, dated, attributed and expiring. A permanent change belongs in the knowledge base, not here.';

CREATE TABLE IF NOT EXISTS kb_override_audit (
    audit_id BIGSERIAL PRIMARY KEY,
    action TEXT NOT NULL CHECK (action IN ('CREATED','REVOKED','REFUSED','APPLIED')),
    rule_id TEXT NOT NULL,
    override_id TEXT,
    expert_id TEXT NOT NULL,
    detail TEXT,
    at TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE kb_override_audit IS
 'REFUSED entries matter most. An attempt to override an immutable rule is a governance signal, not an error to discard.';

-- The database refuses an override on an immutable rule even if the
-- application layer is bypassed.
CREATE OR REPLACE FUNCTION kb_reject_immutable_override() RETURNS trigger AS $$
DECLARE imm BOOLEAN; reason TEXT;
BEGIN
    SELECT immutable, immutable_reason INTO imm, reason
    FROM kb_rules WHERE rule_id = NEW.rule_id;
    IF imm THEN
        INSERT INTO kb_override_audit (action, rule_id, expert_id, detail)
        VALUES ('REFUSED', NEW.rule_id, NEW.expert_id, coalesce(reason, 'immutable rule'));
        RAISE EXCEPTION 'Rule % is immutable and cannot be overridden: %',
              NEW.rule_id, coalesce(reason, 'safety or legal constraint');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_reject_immutable_override ON kb_overrides;
CREATE TRIGGER trg_reject_immutable_override
    BEFORE INSERT ON kb_overrides
    FOR EACH ROW EXECUTE FUNCTION kb_reject_immutable_override();

-- ---------------------------------------------------------------------------
-- Engine runtime state
--
-- Found by running the runner the way it will actually be deployed: as a
-- scheduled job, so every run is a fresh process. Notification state lived in
-- memory, and five pre-season days produced 5 messages with one long-lived
-- process and 20 with a fresh process each day — the same four rules daily.
-- The notification policy only works if it remembers what was already said.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS engine_state (
    plot_id   TEXT PRIMARY KEY,
    version   INT NOT NULL,
    last_run  DATE,
    saved_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload   JSONB NOT NULL
);
COMMENT ON TABLE engine_state IS
 'Notifier ladders, event edges, answered diagnostics and live overrides. Without this the daily job replays every standing advisory on every run.';
COMMENT ON COLUMN engine_state.version IS
 'A bump means the state shape changed. The loader resets rather than half-restoring, and reports why.';

CREATE TABLE IF NOT EXISTS advisory_log (
    plot_id   TEXT NOT NULL,
    day       DATE NOT NULL,
    rule_id   TEXT NOT NULL REFERENCES kb_rules(rule_id),
    severity  TEXT NOT NULL,
    message   TEXT NOT NULL,
    delivered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    acted_on  BOOLEAN,
    acted_at  DATE,
    PRIMARY KEY (plot_id, day, rule_id)
);
COMMENT ON COLUMN advisory_log.acted_on IS
 'The action compliance rate is the primary success metric (Domain 12 D12-EVAL-001). It cannot be computed without this column.';

CREATE INDEX IF NOT EXISTS advisory_log_plot_day ON advisory_log (plot_id, day DESC);

CREATE TABLE IF NOT EXISTS kb_open_items (
    open_item_id TEXT PRIMARY KEY,
    domain_id INT NOT NULL REFERENCES kb_domains(domain_id),
    item TEXT NOT NULL,
    owner TEXT NOT NULL,
    source_class TEXT NOT NULL REFERENCES kb_source_classes(source_class),
    blocking BOOLEAN NOT NULL DEFAULT FALSE,
    time_sensitive BOOLEAN NOT NULL DEFAULT FALSE,
    note TEXT,
    resolved_at TIMESTAMPTZ
);

-- ---------------------------------------------------------------------------
-- Reference data
-- ---------------------------------------------------------------------------

INSERT INTO kb_source_tiers (tier, description) VALUES
 ('A','Institutional Maharashtra source or peer-reviewed research'),
 ('B','Extension portal or national institutional source'),
 ('C','Commercial or blog source; yield and profit figures treated as unreliable')
ON CONFLICT (tier) DO NOTHING;

INSERT INTO kb_source_classes (source_class, description, production_allowed) VALUES
 ('SRC-Q','Quantified figure taken directly from a source', TRUE),
 ('SRC-D','Descriptive statement in source; value inferred', TRUE),
 ('DERIVED','Computed from other classified values', TRUE),
 ('EST','Estimated by author; no source', TRUE),
 ('FIELD','To be measured on the plot', FALSE),
 ('VERIFY','Must be confirmed with a named institution before production use', FALSE)
ON CONFLICT (source_class) DO NOTHING;

INSERT INTO kb_stages VALUES
 ('G0','pre_season','हंगामापूर्वी',-60,0,'highest',FALSE,'none'),
 ('G1','sprouting','उगवण',0,35,'high',TRUE,'none'),
 ('G2','vegetative_tillering','वाढ आणि फुटवा',35,90,'medium_high',FALSE,'partial'),
 ('G3','rhizome_initiation','गड्डा तयार होणे',90,150,'highest',TRUE,'none'),
 ('G4','rhizome_bulking','गड्डा भरणे',150,210,'highest',TRUE,'none'),
 ('G5','maturation','पक्वता',210,240,'medium',FALSE,'none')
ON CONFLICT (stage_code) DO NOTHING;

""")

    # ---- domains ----
    w("-- ---------------------------------------------------------------------------\n")
    w("-- Domains\n")
    w("-- ---------------------------------------------------------------------------\n\n")
    for did, fname, d in domains:
        m = d["metadata"]
        cf = d.get("reference_data", {})
        central = m.get("central_finding", {})
        central_txt = central.get("statement") if isinstance(central, dict) else central
        w("INSERT INTO kb_domains (domain_id,name_en,name_mr,crop,source_document,version,"
          "status,agronomist_validated,total_rules,review_by,purpose,central_finding,author_note) VALUES\n")
        w(f" ({did}, {q(m['domain_name'])}, {q(m['domain_name_mr'])}, {q(CROP)}, "
          f"{q(m.get('source_document'))}, {q(m['version'])}, {q(m['status'])}, "
          f"{q(m.get('agronomist_validated', False))}, {m['total_rules']}, "
          f"{q(m.get('review_by'))}, {q(m.get('purpose'))}, {q(central_txt)}, "
          f"{q(d.get('author_note'))})\n")
        w("ON CONFLICT (domain_id) DO NOTHING;\n\n")

    # ---- categories ----
    w("-- ---------------------------------------------------------------------------\n")
    w("-- Rule categories\n")
    w("-- ---------------------------------------------------------------------------\n\n")
    w("INSERT INTO kb_rule_categories (domain_id, category, description) VALUES\n")
    rows = [f" ({did}, {q(code)}, {q(desc)})" for (did, code), desc in sorted(cats.items())]
    w(",\n".join(rows))
    w("\nON CONFLICT DO NOTHING;\n\n")

    # ---- fields ----
    w("-- ---------------------------------------------------------------------------\n")
    w(f"-- Farm Brain fields ({len(fields)} declared)\n")
    w("-- ---------------------------------------------------------------------------\n\n")
    w("INSERT INTO kb_farm_brain_fields (field_name, spec, declared_in_domain) VALUES\n")
    rows = [f" ({q(n)}, {q(spec)}, {did})" for n, (spec, did) in sorted(fields.items())]
    w(",\n".join(rows))
    w("\nON CONFLICT (field_name) DO NOTHING;\n\n")

    # ---- rules ----
    total = 0
    for did, fname, d in domains:
        w("-- ---------------------------------------------------------------------------\n")
        w(f"-- Domain {did}: {d['metadata']['domain_name']} ({len(d['rules'])} rules)\n")
        w("-- ---------------------------------------------------------------------------\n\n")
        for r in d["rules"]:
            total += 1
            w("INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,"
              "trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,"
              "action_en,action_mr,agronomic_basis,yield_impact,"
              "confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES\n")
            rz = r["reasoning"]
            w(f" ({q(r['rule_id'])}, {did}, {q(r['category'])}, {r['priority']}, {q(r['severity'])}, "
              f"{q(r.get('stage'))},\n")
            w(f"  {q(r['trigger']['english'])},\n  {q(r['trigger']['marathi'])},\n")
            w(f"  {q(r['trigger'].get('expr'))}, {q(r['trigger'].get('expr_version'))}, {q(r.get('delivery'))}, "
              f"{q(r.get('immutable', False))}, {q(r.get('immutable_reason'))},\n")
            w(f"  {q(r['action']['english'])},\n  {q(r['action']['marathi'])},\n")
            w(f"  {q(rz['agronomic_basis'])},\n  {q(rz.get('yield_impact'))},\n")
            w(f"  {rz['confidence_score']}, {q(rz['source_tier'])}, {q(r['source_class'])}, "
              f"{q(r.get('u_value'))}, {q(r['recoverability'])},\n")
            w(f"  {q(r['kannad_note'])});\n\n")

            fl = r["farm_brain_schema"]
            if fl:
                w("INSERT INTO kb_rule_fields (rule_id, field_name) VALUES\n")
                w(",\n".join(f" ({q(r['rule_id'])}, {q(f)})" for f in fl))
                w("\nON CONFLICT DO NOTHING;\n\n")

            gts = r['trigger'].get('golden_tests', [])
            if gts:
                w("INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES\n")
                w(",\n".join(
                    f" ({q(r['rule_id'])}, {i}, {q(json.dumps(t['context'], ensure_ascii=False))}::jsonb, "
                    f"{q(t['expect'])}, {q(t.get('label'))})" for i, t in enumerate(gts)))
                w("\nON CONFLICT DO NOTHING;\n\n")

            refs = rz.get("references", [])
            if refs:
                w("INSERT INTO kb_rule_references (rule_id, reference) VALUES\n")
                w(",\n".join(f" ({q(r['rule_id'])}, {q(x)})" for x in dict.fromkeys(refs)))
                w("\nON CONFLICT DO NOTHING;\n\n")

            deps = []
            for direction in ("feeds_into", "depends_on"):
                for tgt in r["cross_domain_dependencies"].get(direction, []):
                    deps.append((direction, DOMAIN_NAME_TO_ID[tgt]))
            deps = list(dict.fromkeys(deps))
            if deps:
                w("INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES\n")
                w(",\n".join(f" ({q(r['rule_id'])}, {q(dr)}, {t})" for dr, t in deps))
                w("\nON CONFLICT DO NOTHING;\n\n")

    # ---- duplication groups ----
    w("-- ---------------------------------------------------------------------------\n")
    w(f"-- Duplication groups ({len(dupgroups)}) — enforced count-once\n")
    w("-- ---------------------------------------------------------------------------\n\n")
    w("INSERT INTO kb_duplication_groups (group_name, u_value, count_once, note) VALUES\n")
    rows = [f" ({q(g['group'])}, {q(g.get('u_value'))}, {q(g.get('count_once', True))}, {q(g.get('note'))})"
            for g in dupgroups]
    w(",\n".join(rows))
    w("\nON CONFLICT (group_name) DO NOTHING;\n\n")

    w("INSERT INTO kb_duplication_members (group_name, rule_id) VALUES\n")
    rows = [f" ({q(g['group'])}, {q(rid)})" for g in dupgroups for rid in g["rules"]]
    w(",\n".join(rows))
    w("\nON CONFLICT DO NOTHING;\n\n")

    if chain_policy:
        w(f"COMMENT ON TABLE kb_duplication_members IS {q(chain_policy)};\n\n")

    # ---- precedence ----
    prec = None
    for did, fname, dd in domains:
        prec = dd['_schema'].get('additions', {}).get('precedence')
        if prec: break
    if prec:
        w("-- ---------------------------------------------------------------------------\n")
        w(f"-- Precedence graph ({len(prec['graph'])} typed relations)\n")
        w("-- ---------------------------------------------------------------------------\n\n")
        w("INSERT INTO kb_precedence (subject_rule, relation, object_rule, reason_en, reason_mr) VALUES\n")
        w(",\n".join(f" ({q(g['subject'])}, {q(g['relation'])}, {q(g['object'])}, "
                     f"{q(g['reason_en'])}, {q(g['reason_mr'])})" for g in prec['graph']))
        w("\nON CONFLICT DO NOTHING;\n\n")

    # ---- open items ----
    w("-- ---------------------------------------------------------------------------\n")
    w("-- Open items\n")
    w("-- ---------------------------------------------------------------------------\n\n")
    w("INSERT INTO kb_open_items (open_item_id,domain_id,item,owner,source_class,"
      "blocking,time_sensitive,note) VALUES\n")
    rows = []
    for did, fname, d in domains:
        for o in d.get("open_items", []):
            rows.append(f" ({q(o['id'])}, {did}, {q(o['item'])}, {q(o['owner'])}, "
                        f"{q(o['source_class'])}, {q(o.get('blocking', False))}, "
                        f"{q(o.get('time_sensitive', False))}, {q(o.get('note'))})")
    w(",\n".join(rows))
    w("\nON CONFLICT (open_item_id) DO NOTHING;\n\n")

    # ---- views ----
    w("""-- ---------------------------------------------------------------------------
-- Views
-- ---------------------------------------------------------------------------

-- Cumulative loss with duplication groups collapsed to one contribution each.
-- This is the whole reason for consolidating into one store.
CREATE OR REPLACE VIEW v_u_values_deduplicated AS
WITH grouped AS (
    SELECT g.group_name AS factor, g.u_value,
           string_agg(m.rule_id, ', ' ORDER BY m.rule_id) AS contributing_rules
    FROM kb_duplication_groups g
    JOIN kb_duplication_members m ON m.group_name = g.group_name
    WHERE g.u_value IS NOT NULL AND g.count_once
    GROUP BY g.group_name, g.u_value
),
ungrouped AS (
    SELECT r.rule_id AS factor, r.u_value, r.rule_id AS contributing_rules
    FROM kb_rules r
    LEFT JOIN kb_duplication_members m ON m.rule_id = r.rule_id
    WHERE r.u_value IS NOT NULL AND m.rule_id IS NULL
)
SELECT * FROM grouped UNION ALL SELECT * FROM ungrouped;

COMMENT ON VIEW v_u_values_deduplicated IS
 'Each factor contributes exactly once. Summing raw kb_rules.u_value instead would count the cyclone factor three times and make every prediction pessimistic.';

-- Identical action text outside a declared duplication group. Expect zero rows.
CREATE OR REPLACE VIEW v_unintended_duplicate_actions AS
SELECT md5(r.action_en) AS action_hash,
       string_agg(r.rule_id, ', ' ORDER BY r.rule_id) AS rules,
       count(*) AS n
FROM kb_rules r
LEFT JOIN kb_duplication_members m ON m.rule_id = r.rule_id
GROUP BY md5(r.action_en)
HAVING count(*) > 1
   AND count(DISTINCT coalesce(m.group_name, r.rule_id)) > 1;

COMMENT ON VIEW v_unintended_duplicate_actions IS
 'Two rules with the same action text are fine if declared as one duplication group. Outside a group it is an unintended duplicate.';

-- Everything due at a given crop stage, ordered by the Domain 11 priority formula
CREATE OR REPLACE VIEW v_rules_by_stage AS
SELECT r.stage_code, r.rule_id, r.domain_id, d.name_en AS domain, r.category,
       r.severity, r.priority, r.u_value, r.recoverability,
       round(coalesce(r.u_value,0)
             * CASE WHEN r.recoverability='none' THEN 2.0 ELSE 1.0 END, 4) AS priority_score,
       r.action_mr
FROM kb_rules r JOIN kb_domains d ON d.domain_id = r.domain_id
ORDER BY r.stage_code NULLS FIRST, priority_score DESC, r.priority DESC;

-- Rules that are ready to run: they have a formal trigger and golden tests
CREATE OR REPLACE VIEW v_executable_rules AS
SELECT r.rule_id, r.domain_id, r.severity, r.stage_code, r.u_value,
       r.trigger_expr, count(t.seq) AS golden_tests
FROM kb_rules r
LEFT JOIN kb_golden_tests t ON t.rule_id = r.rule_id
WHERE r.trigger_expr IS NOT NULL
GROUP BY r.rule_id, r.domain_id, r.severity, r.stage_code, r.u_value, r.trigger_expr
ORDER BY r.severity, r.u_value DESC NULLS LAST;

-- Rules that still need a trigger written. Expect the count to fall each wave.
CREATE OR REPLACE VIEW v_pending_triggers AS
SELECT r.rule_id, r.domain_id, r.severity, r.u_value, r.trigger_en
FROM kb_rules r
WHERE r.trigger_expr IS NULL
ORDER BY (r.severity='blocking') DESC, (r.severity='red') DESC, r.u_value DESC NULLS LAST;

-- What a rule suppresses and what suppresses it
CREATE OR REPLACE VIEW v_rule_precedence AS
SELECT r.rule_id, r.severity, r.domain_id,
       coalesce(string_agg(DISTINCT p1.object_rule || ' (' || p1.relation || ')', ', '), '-') AS acts_on,
       coalesce(string_agg(DISTINCT p2.subject_rule || ' (' || p2.relation || ')', ', '), '-') AS acted_on_by
FROM kb_rules r
LEFT JOIN kb_precedence p1 ON p1.subject_rule = r.rule_id
LEFT JOIN kb_precedence p2 ON p2.object_rule  = r.rule_id
GROUP BY r.rule_id, r.severity, r.domain_id
HAVING count(p1.*) > 0 OR count(p2.*) > 0;

-- Instruction rules with no declared relation to any blocking rule that shares
-- their fields. These are the pairs most likely to produce contradictory advice.
CREATE OR REPLACE VIEW v_unguarded_instructions AS
SELECT DISTINCT a.rule_id AS instruction, b.rule_id AS potential_blocker,
       count(*) OVER (PARTITION BY a.rule_id, b.rule_id) AS shared_fields
FROM kb_rules a
JOIN kb_rule_fields fa ON fa.rule_id = a.rule_id
JOIN kb_rule_fields fb ON fb.field_name = fa.field_name
JOIN kb_rules b ON b.rule_id = fb.rule_id AND b.rule_id <> a.rule_id
WHERE b.severity IN ('blocking','red')
  AND a.severity NOT IN ('blocking','red')
  AND coalesce(a.stage_code,'') = coalesce(b.stage_code,'')
  AND NOT EXISTS (SELECT 1 FROM kb_precedence p
                  WHERE (p.subject_rule = b.rule_id AND p.object_rule = a.rule_id)
                     OR (p.subject_rule = a.rule_id AND p.object_rule = b.rule_id));

COMMENT ON VIEW v_unguarded_instructions IS
 'Review queue, not an error list. Most pairs are harmless; the point is that none should be unexamined.';

-- Live overrides, narrowest scope first
CREATE OR REPLACE VIEW v_active_overrides AS
SELECT o.override_id, o.rule_id, r.severity AS base_severity, o.kind, o.scope, o.scope_id,
       o.expert_name, o.rationale_mr, o.expires,
       (o.expires - current_date) AS days_left,
       o.applied_count
FROM kb_overrides o JOIN kb_rules r USING (rule_id)
WHERE o.revoked IS NULL AND current_date BETWEEN o.created AND o.expires
ORDER BY CASE o.scope WHEN 'plot' THEN 0 WHEN 'cluster' THEN 1 ELSE 2 END, o.created DESC;

-- Overrides nobody is using, and overrides about to lapse
CREATE OR REPLACE VIEW v_override_review AS
SELECT override_id, rule_id, scope, expert_name, expires,
       (expires - current_date) AS days_left, applied_count,
       CASE WHEN applied_count = 0 THEN 'कधीच लागू झाला नाही'
            WHEN (expires - current_date) <= 30 THEN 'मुदत संपत आहे'
            ELSE 'सक्रिय' END AS flag
FROM kb_overrides
WHERE revoked IS NULL AND current_date <= expires
ORDER BY days_left;

-- The immutable core, with the reason each rule is in it
CREATE OR REPLACE VIEW v_immutable_rules AS
SELECT rule_id, domain_id, severity, immutable_reason, action_en
FROM kb_rules WHERE immutable ORDER BY domain_id, rule_id;

-- Action compliance rate — the metric Domain 12 names as primary
CREATE OR REPLACE VIEW v_compliance AS
SELECT plot_id,
       count(*) FILTER (WHERE acted_on IS NOT NULL)               AS answered,
       count(*) FILTER (WHERE acted_on)                            AS completed,
       count(*)                                                    AS issued,
       round(100.0 * count(*) FILTER (WHERE acted_on)
             / nullif(count(*) FILTER (WHERE acted_on IS NOT NULL), 0), 1) AS compliance_pct
FROM advisory_log GROUP BY plot_id;

-- Plots whose daily job has stopped running
CREATE OR REPLACE VIEW v_stale_plots AS
SELECT plot_id, last_run, (current_date - last_run) AS days_since_run
FROM engine_state
WHERE last_run IS NULL OR last_run < current_date - 2
ORDER BY days_since_run DESC NULLS FIRST;

-- Which rules the farmer acts on, and which he ignores
CREATE OR REPLACE VIEW v_rule_effectiveness AS
SELECT l.rule_id, r.domain_id, r.severity, r.u_value, r.delivery,
       count(*) AS issued,
       count(*) FILTER (WHERE l.acted_on) AS completed,
       round(100.0 * count(*) FILTER (WHERE l.acted_on)
             / nullif(count(*) FILTER (WHERE l.acted_on IS NOT NULL), 0), 1) AS compliance_pct
FROM advisory_log l JOIN kb_rules r USING (rule_id)
GROUP BY l.rule_id, r.domain_id, r.severity, r.u_value, r.delivery
ORDER BY r.u_value DESC NULLS LAST;

COMMENT ON VIEW v_rule_effectiveness IS
 'A high-u_value rule with low compliance is either badly worded or asking for something the farmer cannot do. Both are learnable and neither is visible without this.';

-- Everything that stops the engine
CREATE OR REPLACE VIEW v_blocking AS
SELECT 'rule' AS kind, r.rule_id AS id, r.domain_id, r.action_en AS detail
FROM kb_rules r WHERE r.severity = 'blocking'
UNION ALL
SELECT 'open_item', o.open_item_id, o.domain_id, o.item
FROM kb_open_items o WHERE o.blocking AND o.resolved_at IS NULL;

-- Zero and near-zero cost, irrecoverable, high value — the advisory core
CREATE OR REPLACE VIEW v_high_value_free AS
SELECT r.rule_id, r.domain_id, r.stage_code, r.u_value, r.action_mr, r.kannad_note
FROM kb_rules r
WHERE r.u_value >= 0.10 AND r.recoverability = 'none'
ORDER BY r.u_value DESC;

-- Domains whose content expires
CREATE OR REPLACE VIEW v_expiring AS
SELECT domain_id, name_en, review_by,
       (review_by < current_date) AS stale
FROM kb_domains WHERE review_by IS NOT NULL ORDER BY review_by;

COMMIT;

-- ============================================================================
-- POST-LOAD VERIFICATION — every query should return the stated result
-- ============================================================================
-- 1. rule count
--    SELECT count(*) FROM kb_rules;                        -- expect """ + str(total) + """
-- 2. declared vs actual per domain (expect 0 rows)
--    SELECT d.domain_id, d.total_rules, count(r.rule_id)
--    FROM kb_domains d LEFT JOIN kb_rules r USING (domain_id)
--    GROUP BY d.domain_id, d.total_rules HAVING d.total_rules <> count(r.rule_id);
-- 3. no rule in two duplication groups (expect 0 rows)
--    SELECT rule_id, count(*) FROM kb_duplication_members
--    GROUP BY rule_id HAVING count(*) > 1;
-- 4. deduplicated factor count
--    SELECT count(*), round(1 - exp(sum(ln(1 - u_value))), 4) AS max_theoretical_loss
--    FROM v_u_values_deduplicated;
-- 5. what is still blocking
--    SELECT * FROM v_blocking ORDER BY kind, id;
-- 5c. runtime
--    SELECT * FROM v_stale_plots;                    -- daily job not running
--    SELECT * FROM v_compliance;
--    SELECT * FROM v_rule_effectiveness WHERE u_value > 0.1 AND compliance_pct < 60;
-- 5b. override governance
--    SELECT * FROM v_immutable_rules;                    -- the core that cannot move
--    SELECT * FROM v_active_overrides;
--    SELECT * FROM v_override_review WHERE flag <> 'सक्रिय';
--    SELECT action, count(*) FROM kb_override_audit GROUP BY action;
-- 5a. precedence
--    SELECT relation, count(*) FROM kb_precedence GROUP BY relation;
--    SELECT * FROM v_unguarded_instructions LIMIT 20;
-- 6a. executable coverage
--    SELECT count(*) FROM v_executable_rules;
--    SELECT count(*) FROM v_pending_triggers WHERE severity IN ('blocking','red');  -- expect 0
-- 6. unintended duplicate actions (expect 0 rows)
--    SELECT * FROM v_unintended_duplicate_actions;
-- 7. what is stale
--    SELECT * FROM v_expiring;
-- ============================================================================
""")
    return total


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".")
    ap.add_argument("--out", default="agroguardian_ginger_kb.sql")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    a = ap.parse_args()

    base = Path(a.dir)
    domains = load_domains(base)
    fields = collect_fields(domains)
    cats = collect_categories(domains)
    dupgroups, chain_policy = collect_duplication_groups(domains)

    print(f"Loaded {len(domains)} domains, {sum(len(d['rules']) for _,_,d in domains)} rules")
    print(f"Declared fields: {len(fields)} | categories: {len(cats)} | duplication groups: {len(dupgroups)}")
    print()

    errors, warnings, all_rules, ungrouped_u = validate(domains, fields, cats, dupgroups)

    for wmsg in warnings:
        print("  WARN:", wmsg)
    if warnings:
        print()

    if errors:
        print(f"VALIDATION FAILED — {len(errors)} error(s):")
        for e in errors[:40]:
            print("  ERROR:", e)
        if len(errors) > 40:
            print(f"  ... and {len(errors)-40} more")
        sys.exit(1)

    if a.strict and warnings:
        print("STRICT MODE — warnings treated as errors")
        sys.exit(1)

    print("VALIDATION PASSED")
    print(f"  rule_id globally unique          : {len(all_rules)}")
    print(f"  all farm_brain fields declared   : yes")
    print(f"  all duplication members resolve  : yes")
    print(f"  no filler, no duplicate actions  : yes")
    print(f"  confidence and u_value bounded   : yes")
    print()

    grouped_u = sum(1 for g in dupgroups if g.get("u_value") is not None)
    print(f"  u-value factors after dedup      : {grouped_u} grouped + {len(ungrouped_u)} ungrouped "
          f"= {grouped_u + len(ungrouped_u)}")
    raw_u = sum(1 for _,_,d in domains for r in d["rules"] if r.get("u_value") is not None)
    print(f"  raw u-value rules before dedup   : {raw_u}")
    print(f"  double-counting prevented on     : {raw_u - (grouped_u + len(ungrouped_u))} rules")
    print()

    outp = base / a.out
    with outp.open("w", encoding="utf-8") as f:
        total = emit(domains, fields, cats, dupgroups, chain_policy, f)

    size = outp.stat().st_size
    print(f"WROTE {outp.name}  —  {total} rules, {size//1024} KB")


if __name__ == "__main__":
    main()
