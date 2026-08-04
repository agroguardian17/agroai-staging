#!/usr/bin/env python3
"""
Agro-Guardian AI — Runtime Loader
=================================

Which files actually run in production, and which are build-time only.

The engine imports nine Python files. But four of the data sets it uses exist
twice — once in the build files and once in the knowledge base:

    trigger expressions   triggers_wave1/2/3.py   AND  kb_rules.trigger_expr
    delivery classes      notification_policy.py  AND  kb_rules.delivery
    precedence graph      precedence.py           AND  kb_precedence
    immutable core        expert_override.py      AND  kb_rules.immutable

They agree today because the same converter wrote both. They will not stay in
agreement, because an expert amending a rule edits the JSON and regenerates the
SQL — the .py files are not touched.

So in production the engine must read the database, not the build files.
That reduces the deployable set to SIX files:

    trigger_dsl.py           parser and three-valued evaluator      (pure logic)
    precedence.py            resolver + multi-diagnosis             (logic; graph loaded)
    notification_policy.py   the four delivery behaviours           (logic; map loaded)
    expert_override.py       override API                           (logic; core loaded)
    persistence.py           state across restarts
    runner.py                entry point and message composition
    runtime_loader.py        this file — supplies the data from the DB

The three triggers_wave*.py files and the hard-coded maps inside the other
modules are BUILD-TIME AUTHORING SURFACES. They are how a human writes a rule.
They are not how the engine reads one.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from precedence import Relation

# ---------------------------------------------------------------------------
# Source: knowledge base JSON (development, and the source of truth)
# ---------------------------------------------------------------------------

class JsonSource:
    FILES = ['Domain1_Rules_Ginger_v2.json'] + \
            [f'Domain{i}_Rules_Ginger.json' for i in range(2, 14)]

    def __init__(self, root='.'):
        self.root = Path(root)

    def load(self) -> dict:
        rules, fields, precedence = {}, set(), []
        for fn in self.FILES:
            d = json.loads((self.root / fn).read_text(encoding='utf-8'))
            sch = d['_schema']
            fields |= set(sch.get('farm_brain_fields', {}))
            fields |= set(sch.get('additions', {}).get('new_farm_brain_fields', {}))
            for r in d['rules']:
                rules[r['rule_id']] = r
            g = sch.get('additions', {}).get('precedence', {}).get('graph')
            if g:
                precedence = [Relation(x['subject'], x['relation'], x['object'],
                                       x['reason_en'], x['reason_mr']) for x in g]
        return _assemble(rules, fields, precedence)


# ---------------------------------------------------------------------------
# Source: PostgreSQL (production)
# ---------------------------------------------------------------------------

class PostgresSource:
    """Requires psycopg. The queries are the contract; keep them in sync with json_to_sql.py."""

    Q_RULES = """
        SELECT r.rule_id, r.domain_id, r.category, r.priority, r.severity, r.stage_code,
               r.trigger_en, r.trigger_mr, r.trigger_expr, r.delivery,
               r.immutable, r.immutable_reason,
               r.action_en, r.action_mr, r.agronomic_basis, r.yield_impact,
               r.confidence_score, r.source_tier, r.source_class,
               r.u_value, r.recoverability, r.kannad_note
        FROM kb_rules r
    """
    Q_FIELDS = "SELECT rule_id, field_name FROM kb_rule_fields"
    Q_ALLFIELDS = "SELECT field_name FROM kb_farm_brain_fields"
    Q_PREC = """SELECT subject_rule, relation, object_rule, reason_en, reason_mr
                FROM kb_precedence"""

    def __init__(self, dsn):
        self.dsn = dsn

    def load(self) -> dict:
        import psycopg
        rules, fields = {}, set()
        with psycopg.connect(self.dsn) as c:
            cols = [d.name for d in c.execute(self.Q_RULES).description]
            for row in c.execute(self.Q_RULES):
                d = dict(zip(cols, row, strict=False))
                rules[d['rule_id']] = _shape(d)
            for rid, f in c.execute(self.Q_FIELDS):
                rules[rid]['farm_brain_schema'].append(f)
            fields = {r[0] for r in c.execute(self.Q_ALLFIELDS)}
            precedence = [Relation(*r) for r in c.execute(self.Q_PREC)]
        return _assemble(rules, fields, precedence)


# ---------------------------------------------------------------------------
# Source: SQLite mirror (edge deployment, offline cluster gateway)
# ---------------------------------------------------------------------------

class SqliteSource:
    def __init__(self, path):
        self.path = path

    def load(self) -> dict:
        rules, fields = {}, set()
        with sqlite3.connect(self.path) as c:
            c.row_factory = sqlite3.Row
            for row in c.execute(PostgresSource.Q_RULES.replace('r.', '')):
                d = dict(row)
                rules[d['rule_id']] = _shape(d)
            for rid, f in c.execute(PostgresSource.Q_FIELDS):
                rules[rid]['farm_brain_schema'].append(f)
            fields = {r[0] for r in c.execute(PostgresSource.Q_ALLFIELDS)}
            precedence = [Relation(*r) for r in c.execute(PostgresSource.Q_PREC)]
        return _assemble(rules, fields, precedence)


# ---------------------------------------------------------------------------

def _shape(d: dict) -> dict:
    """A database row into the shape the engine expects."""
    return dict(
        rule_id=d['rule_id'], category=d['category'], priority=d['priority'],
        severity=d['severity'], stage=d['stage_code'],
        delivery=d.get('delivery'), immutable=bool(d.get('immutable')),
        immutable_reason=d.get('immutable_reason'),
        trigger=dict(english=d['trigger_en'], marathi=d['trigger_mr'],
                     expr=d.get('trigger_expr')),
        action=dict(english=d['action_en'], marathi=d['action_mr']),
        reasoning=dict(agronomic_basis=d['agronomic_basis'],
                       yield_impact=d.get('yield_impact'),
                       confidence_score=float(d['confidence_score']),
                       source_tier=d['source_tier'], references=[]),
        cross_domain_dependencies=dict(feeds_into=[], depends_on=[]),
        farm_brain_schema=[],
        u_value=float(d['u_value']) if d.get('u_value') is not None else None,
        recoverability=d['recoverability'], source_class=d['source_class'],
        kannad_note=d['kannad_note'],
    )


def _assemble(rules, fields, precedence) -> dict:
    triggers = {rid: r['trigger']['expr'] for rid, r in rules.items()
                if r['trigger'].get('expr')}
    delivery = {rid: r['delivery'] for rid, r in rules.items() if r.get('delivery')}
    immutable = {rid: (r.get('immutable_reason') or 'immutable')
                 for rid, r in rules.items() if r.get('immutable')}
    return dict(rules=rules, fields=fields, triggers=triggers,
                delivery=delivery, immutable=immutable, precedence=precedence)


# ---------------------------------------------------------------------------

def build_runner(source, *, state_store=None):
    """Wire a Runner from a data source instead of the build-time .py files."""
    import expert_override
    import runner as runner_mod
    from expert_override import OverrideStore
    from notification_policy import Notifier
    from precedence import Precedence
    from trigger_dsl import parse

    data = source.load()

    # the immutable core comes from the database, not the module constant
    expert_override.IMMUTABLE = data['immutable']

    r = runner_mod.Runner.__new__(runner_mod.Runner)
    r.rules = data['rules']
    synth = {'current_month', 'days_to_planting', 'days_to_harvest',
             'brand_name_proposed', 'capability_claim_proposed',
             'profit_guarantee_proposed', 'price_forecast_proposed'}
    r.allowed = data['fields'] | synth | {f + '__duration' for f in data['fields']}
    r.compiled = {rid: parse(expr, r.allowed) for rid, expr in data['triggers'].items()}
    r.prec = Precedence(data['precedence'])
    r.notifier = Notifier(delivery=data['delivery'])
    r.overrides = OverrideStore(data['rules'])

    if state_store:
        from persistence import PersistentRunner
        return PersistentRunner(store=state_store, runner=r)
    return r


if __name__ == '__main__':
    from datetime import date

    from runner import demo_context

    print("═══ build फाइल्समधून वाचल्यास ═══\n")
    from runner import Runner
    a = Runner()
    print(f"  नियम {len(a.rules)} · triggers {len(a.compiled)} · "
          f"संबंध {len(a.prec.by_sub)} विषय")

    print("\n═══ knowledge base मधून वाचल्यास ═══\n")
    b = build_runner(JsonSource())
    print(f"  नियम {len(b.rules)} · triggers {len(b.compiled)} · "
          f"संबंध {len(b.prec.by_sub)} विषय")

    print("\n═══ दोन्ही एकाच निकालावर येतात का ═══\n")
    ctx = demo_context('earthing_day')
    d = date(2026, 8, 26)
    ra = a.run(ctx, d)
    rb = b.run(ctx, d)
    ia = [m.rule_id for m in ra['messages']]
    ib = [m.rule_id for m in rb['messages']]
    print(f"  build:  {ia}")
    print(f"  DB   :  {ib}")
    print(f"  {'✅ जुळतात' if ia == ib else '❌ जुळत नाहीत'}")

    import expert_override
    print(f"\n  immutable DB मधून: {len(expert_override.IMMUTABLE)}")
