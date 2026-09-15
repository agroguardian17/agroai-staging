#!/usr/bin/env python3
"""
Run every Wave-1 trigger against its golden tests.

Three things are checked, and all three have to pass:
  1. the expression parses
  2. every field it names is declared in the knowledge base
  3. every golden test produces the expected outcome
"""

import json, sys
from pathlib import Path
from collections import Counter
from trigger_dsl import parse, evaluate, TV
from triggers_wave1 import TRIGGERS as _W1
from triggers_wave2 import TRIGGERS_W2 as _W2
from triggers_wave3 import TRIGGERS_W3 as _W3
TRIGGERS = {**_W1, **_W2, **_W3}

FILES = ['Domain1_Rules_Ginger_v2.json'] + [f'Domain{i}_Rules_Ginger.json' for i in range(2, 14)]

# Fields the evaluator synthesises rather than reading from Farm Brain
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


def main():
    known, rules = load()
    allowed = known | SYNTHETIC
    # duration companions
    allowed |= {f + '__duration' for f in known}

    n_parse = n_field = n_test = 0
    fail_parse, fail_field, fail_test, unknown_rule = [], [], [], []

    for rid, spec in TRIGGERS.items():
        if rid not in rules:
            unknown_rule.append(rid); continue

        # 1. parse
        try:
            node = parse(spec['expr'], allowed)
            n_parse += 1
        except Exception as e:
            fail_parse.append((rid, str(e))); continue

        # 2. fields declared
        undeclared = sorted(f for f in node.fields()
                            if f not in allowed and not f.endswith('__duration'))
        if undeclared:
            fail_field.append((rid, undeclared))
        else:
            n_field += 1

        # 3. golden tests
        for ctx, expected, label in spec['tests']:
            r = evaluate(node, ctx)
            if r.outcome == expected:
                n_test += 1
            else:
                fail_test.append((rid, label, expected, r.outcome, r.why(), ctx))

    total_tests = sum(len(s['tests']) for s in TRIGGERS.values())

    print("═══ WAVE 1 — TRIGGER DSL ═══\n")
    print(f"  नियम           : {len(TRIGGERS)}")
    print(f"  parse झाले     : {n_parse}/{len(TRIGGERS)}")
    print(f"  fields घोषित   : {n_field}/{n_parse}")
    print(f"  golden tests   : {n_test}/{total_tests}")
    print()

    if unknown_rule:
        print(f"  ❌ knowledge base मध्ये नसलेले rule_id: {unknown_rule}\n")
    for rid, e in fail_parse:
        print(f"  ❌ PARSE  {rid}: {e}")
    for rid, u in fail_field:
        print(f"  ❌ FIELD  {rid}: undeclared {u}")
    for rid, label, exp, got, why, ctx in fail_test:
        print(f"  ❌ TEST   {rid}  [{label}]")
        print(f"            अपेक्षित {exp}, मिळाले {got}")
        print(f"            {why}")
        print(f"            ctx={ctx}")

    ok = not (fail_parse or fail_field or fail_test or unknown_rule)
    print()
    print("  ✅ सर्व पास" if ok else "  ❌ अपयश — वर पहा")

    # coverage against the full blocking/red set
    br = {rid for rid, (d, r) in rules.items() if r['severity'] in ('blocking', 'red')
          and r.get('decision_type') in {'AUTO_DECISION','SENSOR_ALERT','SCHEDULED_REMINDER','BLOCK'}}
    done = br & set(TRIGGERS)
    print(f"\n  blocking/red व्याप्ती: {len(done)}/{len(br)}")
    missing = sorted(br - set(TRIGGERS))
    if missing:
        print(f"  उरलेले: {', '.join(missing)}")

    # UNKNOWN behaviour summary — the graceful-degradation guarantee
    unk = Counter()
    for rid, spec in TRIGGERS.items():
        if rid not in rules: continue
        try: node = parse(spec['expr'], allowed)
        except Exception: continue
        for ctx, expected, _ in spec['tests']:
            if expected == TV.UNKNOWN: unk[rid] += 1
    print(f"\n  UNKNOWN वर्तन तपासलेले नियम: {len(unk)}/{len(TRIGGERS)}")
    print("  (माहिती अपुरी असताना नियम FALSE न देता UNKNOWN देतो — Domain 12 ची अट)")

    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
