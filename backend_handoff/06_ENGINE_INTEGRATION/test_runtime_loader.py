#!/usr/bin/env python3
"""
Golden tests for the runtime loader.

The important test is drift: four data sets exist both in the build .py files
and in the knowledge base. They agree today because the same converter wrote
both. This suite fails the build the day they stop agreeing.
"""
import sys, json
from datetime import date
from pathlib import Path
from runtime_loader import JsonSource, build_runner
from runner import Runner, demo_context

fails = []
def check(l, c, d=''):
    if not c: fails.append((l, d))

print("═══ DRIFT: build files vs knowledge base ═══\n")

data = JsonSource().load()

from triggers_wave1 import TRIGGERS as W1
from triggers_wave2 import TRIGGERS_W2 as W2
from triggers_wave3 import TRIGGERS_W3 as W3
try:
    from triggers_wave4_vpd import TRIGGERS_W4 as W4
except ImportError:
    W4 = {}
try:
    from triggers_wave5_d14 import TRIGGERS_W5 as W5
except ImportError:
    W5 = {}
T = {**W1, **W2, **W3, **W4, **W5}
mismatch = [k for k, v in T.items() if data['triggers'].get(k) != v['expr']]
check("trigger expressions जुळतात", not mismatch, f"{len(mismatch)}: {mismatch[:5]}")
check("संख्या जुळते", len(T) == len(data['triggers']),
      f"build {len(T)} vs kb {len(data['triggers'])}")
print(f"  ✅ triggers {len(T)}")

from notification_policy import DELIVERY
dm = [k for k, v in DELIVERY.items() if data['delivery'].get(k) != v]
check("delivery वर्ग जुळतात", not dm, f"{len(dm)}: {dm[:5]}")
print(f"  ✅ delivery {len(DELIVERY)}")

from precedence import PRECEDENCE
pb = {(r.subject, r.relation, r.object) for r in PRECEDENCE}
pk = {(r.subject, r.relation, r.object) for r in data['precedence']}
check("precedence संबंध जुळतात", pb == pk, f"फरक: {sorted(pb ^ pk)[:5]}")
print(f"  ✅ precedence {len(PRECEDENCE)}")

from expert_override import IMMUTABLE
check("immutable यादी जुळते", set(IMMUTABLE) == set(data['immutable']),
      f"फरक: {sorted(set(IMMUTABLE) ^ set(data['immutable']))}")
print(f"  ✅ immutable {len(IMMUTABLE)}")

print("\n═══ दोन्ही मार्ग एकाच निकालावर ═══\n")

for case in ['preseason', 'earthing_day', 'heat_spray', 'saturation', 'quiet']:
    ctx = demo_context(case)
    d = date(2026, 8, 26)
    a = [m.rule_id for m in Runner().run(ctx, d)['messages']]
    b = [m.rule_id for m in build_runner(JsonSource()).run(ctx, d)['messages']]
    check(f"{case}: build == DB", a == b, f"{a} vs {b}")
print("  ✅ पाचही प्रकरणे")

print("\n═══ IMMUTABLE DB मधून येतो ═══\n")

import expert_override
from expert_override import OverrideRefused
r = build_runner(JsonSource())
try:
    r.overrides.create('D05-CH-001', 'DISABLE', 'AG-1', 'x',
                       'या भागात हे लागू होत नाही असे वाटते आहे.',
                       scope='plot', scope_id='P1', day=date(2026, 8, 26),
                       disable_reason_mr='y')
    fails.append(("DB मधील immutable नाकारतो", "स्वीकारला"))
except OverrideRefused:
    print("  ✅ database मधून वाचलेला immutable core तितकाच कडक")

print("\n═══ निकाल ═══\n")
if fails:
    for l, d in fails: print(f"  ❌ {l}\n     {d}")
    print(f"\n  {len(fails)} अपयश"); sys.exit(1)
print("  ✅ सर्व पास")
