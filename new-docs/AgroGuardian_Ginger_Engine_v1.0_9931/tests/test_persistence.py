#!/usr/bin/env python3
"""
Golden tests for engine state persistence.

Every test simulates the deployment shape: a fresh process for each day.
A test that reuses one object proves nothing about a cron job.
"""
import sys, shutil
from pathlib import Path
from datetime import date, timedelta
from persistence import (PersistentRunner, FileStateStore, SqliteStateStore,
                         load_notifier, dump_notifier, load_overrides, dump_overrides,
                         STATE_VERSION)
from runner import Runner, demo_context
from expert_override import OverrideRefused

fails = []
def check(label, cond, detail=''):
    if not cond: fails.append((label, detail))

def fresh(store_kind='sqlite'):
    """A new process, same storage."""
    return PersistentRunner(store=SqliteStateStore('t.db') if store_kind=='sqlite'
                            else FileStateStore('t_state'))

shutil.rmtree('t_state', ignore_errors=True)
Path('t.db').unlink(missing_ok=True)
ctx = demo_context('preseason')

print("═══ RESTART DOES NOT REPLAY ═══\n")

for kind in ('sqlite', 'file'):
    shutil.rmtree('t_state', ignore_errors=True); Path('t.db').unlink(missing_ok=True)
    counts = []
    for i in range(6):
        d = date(2026,3,1)+timedelta(days=i)
        counts.append(len(fresh(kind).run_day('P1', ctx, d)['messages']))
    check(f"{kind}: पहिल्या दिवशी संदेश", counts[0] > 0, str(counts))
    check(f"{kind}: दुसऱ्या दिवशी पुनरावृत्ती नाही", counts[1] < counts[0], str(counts))
    check(f"{kind}: एकूण फुगत नाही", sum(counts) < counts[0]*3, str(counts))
    print(f"  ✅ {kind:7s} {counts}  एकूण {sum(counts)}")

print("\n═══ EVENT EDGE SURVIVES RESTART ═══\n")

shutil.rmtree('t_state', ignore_errors=True); Path('t.db').unlink(missing_ok=True)
sat = demo_context('saturation')
d1 = fresh().run_day('P2', sat, date(2026,9,10))
d2 = fresh().run_day('P2', sat, date(2026,9,11))
ids1 = {m.rule_id for m in d1['messages']}
ids2 = {m.rule_id for m in d2['messages']}
check("संपृक्ततेचा इशारा दुसऱ्या दिवशी पुन्हा नाही",
      not (ids1 & ids2), f"{ids1 & ids2}")
print(f"  ✅ दिवस १: {len(ids1)} संदेश, दिवस २: {len(ids2)}")

print("\n═══ OVERRIDE SURVIVES RESTART ═══\n")

shutil.rmtree('t_state', ignore_errors=True); Path('t.db').unlink(missing_ok=True)
pr = fresh()
ov = pr.create_override('P3', rule_id='D02-DR-001', kind='THRESHOLD',
    expert_id='AG-1', expert_name='डॉ. कदम',
    rationale_mr='या भागातील काळी जमीन खोल आहे आणि खालचा थर वालुकामय आहे.',
    scope='plot', scope_id='P3', day=date(2026,3,6), new_threshold={'from':12,'to':9})
st = SqliteStateStore('t.db').load('P3')
s2 = load_overrides(st.get('overrides'), Runner().rules)
eff = s2.effective('D02-DR-001', date(2026,3,7), plot_id='P3')
check("override restart नंतर सक्रिय", len(eff['overrides'])==1, str(eff['overrides']))
check("बदललेली अट टिकते", 'percolation_time_hours > 9' in eff['expr'], eff['expr'][:60])
check("तज्ज्ञाची ओळख टिकते", eff['overrides'][0]['by']=='डॉ. कदम', str(eff['overrides'][0]))
print("  ✅ override, अट आणि तज्ज्ञाची ओळख टिकली")

print("\n═══ IMMUTABLE CORE STILL REFUSES AFTER RESTART ═══\n")

try:
    fresh().create_override('P3', rule_id='D05-CH-001', kind='DISABLE',
        expert_id='AG-1', expert_name='x',
        rationale_mr='या भागात हे लागू होत नाही असे वाटते आहे.',
        scope='plot', scope_id='P3', day=date(2026,3,7), disable_reason_mr='y')
    fails.append(("immutable restart नंतरही नाकारला जातो", "स्वीकारला"))
except OverrideRefused:
    print("  ✅ persistence ने immutable संरक्षण कमकुवत केले नाही")

print("\n═══ GAP IS REPORTED, NOT REPLAYED ═══\n")

shutil.rmtree('t_state', ignore_errors=True); Path('t.db').unlink(missing_ok=True)
fresh().run_day('P4', ctx, date(2026,3,1))
r = fresh().run_day('P4', ctx, date(2026,3,25))
check("खंड नोंदवला जातो", r['gap_days']==24, str(r['gap_days']))
# 24 days is past the 21-day ladder step, so a reminder is correct.
# What must NOT happen is the whole ladder replaying at once.
from persistence import load_notifier
st = SqliteStateStore('t.db').load('P4')
n = load_notifier(st['notifier'])
over_stepped = [k for k,v in n.issue_count.items() if v > 2]
check("खंडानंतर शिडी उडी मारत नाही", not over_stepped,
      f"एकाच खंडात अनेक पायऱ्या: {over_stepped}")
# 24 days past a run means several standing preconditions come due at once.
# That is correct. What must not happen is a flood.
check("खंडानंतरही मर्यादित संदेश", len(r['messages']) <= 8,
      str([m.rule_id for m in r['messages']]))
print(f"  ✅ {r['gap_days']} दिवसांचा खंड, {len(r['messages'])} संदेश, शिडी एका पायरीने पुढे")

print("\n═══ VERSION MISMATCH RESETS CLEANLY ═══\n")

import sqlite3, json
with sqlite3.connect('t.db') as c:
    c.execute("UPDATE engine_state SET version=? WHERE plot_id='P4'", (STATE_VERSION+9,))
r = fresh().run_day('P4', ctx, date(2026,3,26))
check("आवृत्ती जुळत नसल्यास कारण सांगितले जाते", r['state_reset'] is not None, str(r['state_reset']))
print(f"  ✅ {r['state_reset']}")

print("\n═══ ROUND TRIP IS LOSSLESS ═══\n")

from notification_policy import Notifier
n = Notifier()
n.decide('D03-WS-001', date(2026,3,1))
n.decide('D03-WL-001', date(2026,3,2))
n.resolve('D02-CL-001')
n2 = load_notifier(dump_notifier(n))
check("first_issued टिकते", n2.first_issued==n.first_issued, "")
check("active संच टिकतो", n2.active==n.active, f"{n2.active} vs {n.active}")
check("resolved संच टिकतो", n2.resolved==n.resolved, "")
check("issue_count टिकते", dict(n2.issue_count)==dict(n.issue_count), "")
print("  ✅ notifier स्थिती अखंड")

print("\n═══ ADVISORY LOG ═══\n")
h = SqliteStateStore('t.db').history('P4', 10)
check("नोंद ठेवली जाते", len(h) > 0, str(h))
print(f"  ✅ {len(h)} नोंदी")

shutil.rmtree('t_state', ignore_errors=True); Path('t.db').unlink(missing_ok=True)

print("\n═══ निकाल ═══\n")
if fails:
    for l,d in fails: print(f"  ❌ {l}\n     {d}")
    print(f"\n  {len(fails)} अपयश"); sys.exit(1)
print("  ✅ सर्व पास")
