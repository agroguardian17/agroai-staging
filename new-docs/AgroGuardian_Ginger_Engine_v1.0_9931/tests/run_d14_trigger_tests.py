#!/usr/bin/env python3
"""
Run every Wave-5 (Domain 14) trigger against its golden tests.

Same three checks as run_trigger_tests.py:
  1. the expression parses
  2. every field it names is declared in the knowledge base
  3. every golden test produces the expected outcome

Additive: reads the same DSL parser and evaluator, loads D1-D14 (not D1-D13),
loads wave5 in addition to waves 1-3. Does not touch original test runner.
"""

import json, sys
from pathlib import Path
from collections import Counter
from trigger_dsl import parse, evaluate, TV

# All waves — D14 is wave 5 (VPD retrofit is wave 4, kept for completeness)
from triggers_wave1 import TRIGGERS as _W1
from triggers_wave2 import TRIGGERS_W2 as _W2
from triggers_wave3 import TRIGGERS_W3 as _W3
try:
    from triggers_wave4_vpd import TRIGGERS_W4 as _W4
except ImportError:
    _W4 = {}
from triggers_wave5_d14 import TRIGGERS_W5 as _W5

ALL_TRIGGERS = {**_W1, **_W2, **_W3, **_W4, **_W5}
D14_TRIGGERS = _W5

FILES = ['Domain1_Rules_Ginger_v2.json'] + [f'Domain{i}_Rules_Ginger.json' for i in range(2, 15)]

SYNTHETIC = {
    'current_month', 'days_to_planting', 'days_to_harvest',
    'brand_name_proposed', 'capability_claim_proposed',
    'profit_guarantee_proposed', 'price_forecast_proposed',
}


def load():
    fields, rules = set(), {}
    for fn in FILES:
        d = json.loads(Path(fn).read_text(encoding='utf-8'))
        sch = d['_schema']
        fields |= set(sch.get('farm_brain_fields', {}))
        fields |= set(sch.get('additions', {}).get('new_farm_brain_fields', {}))
        for r in d['rules']:
            rules[r['rule_id']] = (d['metadata']['domain'], r)
    return fields, rules


def run(scope, label):
    known, rules = load()
    allowed = known | SYNTHETIC
    allowed |= {f + '__duration' for f in known}

    n_parse = n_field = n_test = 0
    fail_parse, fail_field, fail_test, unknown_rule = [], [], [], []

    for rid, spec in scope.items():
        if rid not in rules:
            unknown_rule.append(rid); continue
        try:
            node = parse(spec['expr'], allowed)
            n_parse += 1
        except Exception as e:
            fail_parse.append((rid, str(e))); continue

        undeclared = sorted(f for f in node.fields()
                            if f not in allowed and not f.endswith('__duration'))
        if undeclared:
            fail_field.append((rid, undeclared))
        else:
            n_field += 1

        for ctx, expected, tlabel in spec['tests']:
            r = evaluate(node, ctx)
            if r.outcome == expected:
                n_test += 1
            else:
                fail_test.append((rid, tlabel, expected, r.outcome, r.why(), ctx))

    total_tests = sum(len(s['tests']) for s in scope.values())

    print(f"═══ {label} — TRIGGER DSL ═══\n")
    print(f"  नियम           : {len(scope)}")
    print(f"  parse झाले     : {n_parse}/{len(scope)}")
    print(f"  fields घोषित   : {n_field}/{n_parse}")
    print(f"  golden tests   : {n_test}/{total_tests}")
    print()

    if unknown_rule:
        print(f"  ❌ knowledge base मध्ये नसलेले rule_id: {unknown_rule}\n")
    for rid, e in fail_parse:
        print(f"  ❌ PARSE  {rid}: {e}")
    for rid, u in fail_field:
        print(f"  ❌ FIELD  {rid}: undeclared {u}")
    for rid, tlabel, exp, got, why, ctx in fail_test[:20]:
        print(f"  ❌ TEST   {rid}  [{tlabel}]")
        print(f"            अपेक्षित {exp}, मिळाले {got}")
        print(f"            {why}")
        print(f"            ctx={ctx}")
    if len(fail_test) > 20:
        print(f"  ... आणि {len(fail_test) - 20} अधिक test failures")

    ok = not (fail_parse or fail_field or fail_test or unknown_rule)
    print()
    print(f"  {'✅ सर्व पास' if ok else '❌ अपयश'} — {label}")
    print()
    return ok


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  D14 TRIGGER TEST SUITE")
    print("="*60 + "\n")

    d14_ok = run(D14_TRIGGERS, "WAVE 5 (Domain 14 — 47 rules)")

    print("\n" + "-"*60)
    print("  Regression check — all waves 1-5 together")
    print("-"*60 + "\n")
    all_ok = run(ALL_TRIGGERS, f"WAVES 1-5 (all {len(ALL_TRIGGERS)} rules)")

    sys.exit(0 if (d14_ok and all_ok) else 1)
