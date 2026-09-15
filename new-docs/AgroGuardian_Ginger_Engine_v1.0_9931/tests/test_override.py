#!/usr/bin/env python3
"""
Golden tests for expert override.

The tests that matter are the refusals. An override system that accepts
everything is not a governance layer, it is a back door.
"""

import sys
from datetime import date, timedelta
from expert_override import (OverrideStore, OverrideRefused, IMMUTABLE, load_rules,
                             DEFAULT_EXPIRY_DAYS, MAX_EXPIRY_DAYS)

rules = load_rules()
DAY = date(2026, 8, 15)
fails = []
LONG = 'या भागातील परिस्थिती वेगळी आहे आणि अनुभवावरून हा बदल आवश्यक वाटतो, म्हणून तो प्रस्तावित करत आहे.'


def st():
    return OverrideStore(rules)


def must_accept(label, fn):
    try:
        return fn()
    except OverrideRefused as e:
        fails.append((label, f"नाकारला, पण स्वीकारायला हवा होता: {e}"))
        return None


def must_refuse(label, fn, expect_word=None):
    try:
        fn()
        fails.append((label, "स्वीकारला, पण नाकारायला हवा होता"))
    except OverrideRefused as e:
        if expect_word and expect_word not in str(e):
            fails.append((label, f"नाकारला पण चुकीच्या कारणाने: {e}"))


print("═══ IMMUTABLE CORE ═══\n")

# every immutable rule must refuse every kind of override
KINDS = [('DISABLE', {'disable_reason_mr': 'x'}),
         ('SEVERITY', {'new_severity': 'info'}),
         ('DELIVERY', {'new_delivery': 'SILENT_GUARD'})]

for rid in IMMUTABLE:
    if rid not in rules:
        fails.append((f"IMMUTABLE {rid}", "knowledge base मध्ये असा नियम नाही"))
        continue
    for kind, kw in KINDS:
        must_refuse(f"{rid} {kind}",
                    lambda r=rid, k=kind, w=kw: st().create(
                        r, k, 'AG-1', 'x', LONG, scope='global', day=DAY, **w),
                    expect_word='बदलता येत नाही')

print(f"  {len(IMMUTABLE)} immutable नियम × {len(KINDS)} प्रकार तपासले")

print("\n═══ SCOPE AND EXPIRY ═══\n")

must_refuse("कायमस्वरूपी override",
            lambda: st().create('D04-MC-002', 'DELIVERY', 'AG-1', 'x', LONG,
                                scope='plot', scope_id='P1', day=DAY,
                                expiry_days=MAX_EXPIRY_DAYS + 1, new_delivery='EVENT'),
            expect_word='knowledge base')

must_refuse("व्याप्ती ओळखीशिवाय",
            lambda: st().create('D04-MC-002', 'DELIVERY', 'AG-1', 'x', LONG,
                                scope='plot', day=DAY, new_delivery='EVENT'),
            expect_word='ओळख')

must_refuse("कारण खूप छोटे",
            lambda: st().create('D04-MC-002', 'DELIVERY', 'AG-1', 'x', 'छोटे',
                                scope='plot', scope_id='P1', day=DAY, new_delivery='EVENT'),
            expect_word='कारण')

must_refuse("blocking जागतिक बंद",
            lambda: st().create('D02-CL-002', 'DISABLE', 'AG-1', 'x', LONG,
                                scope='global', day=DAY, disable_reason_mr='y'),
            expect_word='जागतिक')

must_refuse("blocking ची तीव्रता कमी",
            lambda: st().create('D02-CL-002', 'SEVERITY', 'AG-1', 'x', LONG,
                                scope='plot', scope_id='P1', day=DAY, new_severity='info'),
            expect_word='DISABLE')

must_refuse("अस्तित्वात नसलेला नियम",
            lambda: st().create('D99-XX-999', 'DISABLE', 'AG-1', 'x', LONG,
                                scope='plot', scope_id='P1', day=DAY, disable_reason_mr='y'))

print("  ✅ व्याप्ती व मुदतीची संरक्षणे")

print("\n═══ THRESHOLD ═══\n")

must_refuse("अटीत नसलेले मूल्य",
            lambda: st().create('D03-MN-004', 'THRESHOLD', 'AG-1', 'x', LONG,
                                scope='plot', scope_id='P1', day=DAY,
                                new_threshold={'from': 999, 'to': 10}),
            expect_word='सापडत नाही')

must_refuse("red नियमाची मर्यादा, छोटे कारण",
            lambda: st().create('D03-MN-004', 'THRESHOLD', 'AG-1', 'x',
                                'दहा दिवस बरे वाटतात इथे',
                                scope='plot', scope_id='P1', day=DAY,
                                new_threshold={'from': 7, 'to': 10}),
            expect_word='सविस्तर')

s = st()
ov = must_accept("वैध threshold बदल",
                 lambda: s.create('D02-DR-001', 'THRESHOLD', 'AG-1', 'डॉ. कदम',
                                  'या भागातील काळी जमीन खोल आहे आणि खालचा थर वालुकामय आहे, '
                                  'त्यामुळे बारा तासांची मर्यादा इथे कडक ठरते.',
                                  scope='cluster', scope_id='C1', day=DAY,
                                  new_threshold={'from': 12, 'to': 9}))
if ov:
    e = s.effective('D02-DR-001', DAY, cluster_id='C1')
    if 'percolation_time_hours > 9' not in e['expr']:
        fails.append(("threshold अटीत उतरला", f"expr: {e['expr'][:70]}"))
    # and must NOT apply to a different cluster
    e2 = s.effective('D02-DR-001', DAY, cluster_id='C2')
    if 'percolation_time_hours > 12' not in e2['expr']:
        fails.append(("व्याप्तीबाहेर लागू झाला", f"expr: {e2['expr'][:70]}"))

print("  ✅ threshold बदल व व्याप्ती")

print("\n═══ PRECEDENCE OF SCOPE ═══\n")

s = st()
s.create('D04-MC-002', 'DELIVERY', 'AG-1', 'x', LONG, scope='global', day=DAY,
         new_delivery='EVENT')
s.create('D04-MC-002', 'DELIVERY', 'AG-2', 'y', LONG, scope='plot', scope_id='P1', day=DAY,
         new_delivery='SILENT_GUARD')
a = s.effective('D04-MC-002', DAY, plot_id='P1')
b = s.effective('D04-MC-002', DAY, plot_id='P2')
if a['delivery'] != 'SILENT_GUARD':
    fails.append(("plot override global ला ओलांडतो", f"got {a['delivery']}"))
if b['delivery'] != 'EVENT':
    fails.append(("इतर plot ला global लागू", f"got {b['delivery']}"))
print("  ✅ अरुंद व्याप्ती जिंकते")

print("\n═══ EXPIRY AND REVOCATION ═══\n")

s = st()
ov = s.create('D04-MC-002', 'DELIVERY', 'AG-1', 'x', LONG, scope='plot', scope_id='P1',
              day=DAY, expiry_days=30, new_delivery='EVENT')
before = s.effective('D04-MC-002', DAY + timedelta(days=10), plot_id='P1')
after = s.effective('D04-MC-002', DAY + timedelta(days=45), plot_id='P1')
if before['delivery'] != 'EVENT':
    fails.append(("मुदतीत लागू", f"got {before['delivery']}"))
if after['delivery'] == 'EVENT':
    fails.append(("मुदत संपल्यावर लागू राहिला", "override expired पण अजून चालू"))

s.revoke(ov.override_id, 'AG-9', DAY + timedelta(days=5))
rev = s.effective('D04-MC-002', DAY + timedelta(days=10), plot_id='P1')
if rev['delivery'] == 'EVENT':
    fails.append(("मागे घेतल्यावर लागू राहिला", "revoked पण अजून चालू"))
must_refuse("दोनदा मागे घेणे",
            lambda: s.revoke(ov.override_id, 'AG-9', DAY + timedelta(days=6)))
print("  ✅ मुदत व मागे घेणे")

print("\n═══ AUDIT TRAIL ═══\n")

s = st()
s.create('D04-MC-002', 'DELIVERY', 'AG-1', 'डॉ. कदम', LONG, scope='plot', scope_id='P1',
         day=DAY, new_delivery='EVENT')
try:
    s.create('D05-CH-001', 'DISABLE', 'AG-1', 'x', LONG, scope='global', day=DAY,
             disable_reason_mr='y')
except OverrideRefused:
    pass
kinds = {a['action'] for a in s.audit}
if kinds != {'CREATED', 'REFUSED'}:
    fails.append(("नाकारलेले प्रयत्नही नोंदवले जातात", f"actions {kinds}"))
if not all(a.get('expert_id') for a in s.audit):
    fails.append(("प्रत्येक नोंदीत तज्ज्ञाची ओळख", "expert_id गहाळ"))
print("  ✅ नाकारलेले प्रयत्नही नोंदवले जातात")

print("\n═══ निकाल ═══\n")
if fails:
    for label, why in fails:
        print(f"  ❌ {label}")
        print(f"     {why}")
    print(f"\n  {len(fails)} अपयश")
    sys.exit(1)
print("  ✅ सर्व पास")
