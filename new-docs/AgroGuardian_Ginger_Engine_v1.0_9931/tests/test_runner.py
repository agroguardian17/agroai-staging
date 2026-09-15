#!/usr/bin/env python3
"""
Golden tests for the daily runner.

These check the message, not the rule. Every earlier suite proved the right
rules fire; this proves the farmer can read the result.
"""
import sys, re
from datetime import date
from runner import Runner, demo_context, reads_as_engine_instruction

fails = []
DAY = date(2026, 8, 26)


def check(label, cond, detail=''):
    if not cond:
        fails.append((label, detail))


def day(case):
    r = Runner()
    ctx = demo_context(case)
    return r.run(ctx, DAY), ctx


print("═══ MESSAGE QUALITY ═══\n")

for case in ['preseason', 'earthing_day', 'heat_spray', 'saturation', 'quiet']:
    res, ctx = day(case)
    for m in res['messages']:
        check(f"{case}/{m.rule_id} शेतकरी-भाषा",
              not m.engine_speak, f"engine-भाषेत: {m.what_mr[:56]}")
        check(f"{case}/{m.rule_id} रिकामा नाही",
              len(m.what_mr.strip()) > 10, m.what_mr)
        check(f"{case}/{m.rule_id} पहिले वाक्य आटोपशीर",
              len(m.what_mr) < 220, f"{len(m.what_mr)} अक्षरे")
        # the loss must not be stated twice
        both = m.if_not_mr and ('%' in m.what_mr or 'टक्क' in m.what_mr)
        check(f"{case}/{m.rule_id} नुकसान एकदाच", not both,
              f"{m.what_mr[:40]} + {m.if_not_mr}")
        check(f"{case}/{m.rule_id} bundle कापलेला नाही",
              all(not t.endswith(('सुम', 'अस', 'क्रि')) for t in m.bundled_with),
              str(m.bundled_with))

print(f"  {sum(len(day(c)[0]['messages']) for c in ['preseason','earthing_day','heat_spray','saturation','quiet'])} संदेश तपासले")

print("\n═══ SUPPRESSION REACHES THE FARMER ═══\n")

res, _ = day('heat_spray')
ids = {m.rule_id for m in res['messages']}
check("३९.५° ला फवारणी सुचवली जात नाही", 'D04-MC-001' not in ids,
      f"संदेशांत आहे: {ids}")
check("दडपणे नोंदवले गेले",
      any(a == 'D04-MC-001' for a, _ in res['suppressed']),
      str(res['suppressed']))
print("  ✅ उष्णतेत फवारणी दडपली आणि नोंदवली")

print("\n═══ ORDERING ═══\n")

res, _ = day('saturation')
sev_order = [m.severity for m in res['messages']]
rank = {'blocking': 0, 'red': 1, 'yellow': 2, 'info': 3}
check("तीव्रतेनुसार क्रम", sev_order == sorted(sev_order, key=lambda s: rank[s]),
      str(sev_order))
print(f"  ✅ क्रम: {' > '.join(dict.fromkeys(sev_order))}")

print("\n═══ DIAGNOSIS GATE ═══\n")

res, _ = day('saturation')
check("निदान झाले", res['diagnosis'] and res['diagnosis']['state'] == 'CONFIRMED',
      str(res['diagnosis']['state'] if res['diagnosis'] else None))
res2, _ = day('quiet')
check("लक्षण नसताना निदान नाही",
      res2['diagnosis'] is None or res2['diagnosis']['state'] == 'NO_CANDIDATE',
      str(res2['diagnosis']))
print("  ✅ निदान फक्त लक्षण असतानाच")

print("\n═══ NOTHING TO DO IS A VALID ANSWER ═══\n")

r = Runner()
ctx = demo_context('quiet')
first = r.run(ctx, DAY)
second = r.run(ctx, date(2026, 8, 27))
check("दुसऱ्या दिवशी तेच संदेश पुन्हा येत नाहीत",
      len(second['messages']) < len(first['messages']) or len(first['messages']) == 0,
      f"{len(first['messages'])} -> {len(second['messages'])}")
print(f"  ✅ दिवस १: {len(first['messages'])} संदेश, दिवस २: {len(second['messages'])}")

print("\n═══ UNKNOWN IS REPORTED, NOT GUESSED ═══\n")

r = Runner()
sparse = {'dap': 82, 'current_stage': 'G3', 'current_month': 8}
res = r.run(sparse, DAY)
check("अपुरी माहिती नोंदवली जाते", len(res['unknown']) > 0,
      "unknown रिकामे — गहाळ माहिती गुपचूप FALSE झाली")
named = all(m or w for _, m, w in res['unknown'])
check("गहाळ field चे नाव दिले जाते", named, str(res['unknown'][:2]))
print(f"  ✅ {len(res['unknown'])} नियम UNKNOWN, प्रत्येकात कारण")

print("\n═══ निकाल ═══\n")
if fails:
    for l, d in fails[:20]:
        print(f"  ❌ {l}")
        if d: print(f"     {d}")
    print(f"\n  {len(fails)} अपयश")
    sys.exit(1)
print("  ✅ सर्व पास")
