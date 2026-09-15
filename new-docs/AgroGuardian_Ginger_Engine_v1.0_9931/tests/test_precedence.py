#!/usr/bin/env python3
"""
Golden tests for precedence and multi-diagnosis.

The tests that matter most are the ones proving something does NOT happen:
the spray is not issued in heat, the nitrogen is not recommended before
diagnosis, and an ambiguous case does not silently pick a winner.
"""

import sys
from precedence import Precedence, Fired, diagnose, PRECEDENCE, RELATIONS

P = Precedence()
fails = []

def case(label, fired, *, issued=None, suppressed_ids=None, bundled=None,
         waits=None, escalated_into=None, no_fallback=False):
    d = P.resolve([Fired(*f) for f in fired])
    if issued is not None and set(d.issued) != set(issued):
        fails.append((label, f"issued {sorted(d.issued)} != {sorted(issued)}"))
    if suppressed_ids is not None:
        got = {a for a, _, _ in d.suppressed} | {a for a, _, _ in d.superseded}
        if got != set(suppressed_ids):
            fails.append((label, f"suppressed {sorted(got)} != {sorted(suppressed_ids)}"))
    if bundled is not None and d.bundles != bundled:
        fails.append((label, f"bundles {d.bundles} != {bundled}"))
    if waits is not None:
        got = {a for a, _ in d.sequence_waits}
        if got != set(waits):
            fails.append((label, f"waits {sorted(got)} != {sorted(waits)}"))
    if escalated_into is not None:
        got = {b for _, b in d.escalated}
        if got != set(escalated_into):
            fails.append((label, f"escalated {sorted(got)} != {sorted(escalated_into)}"))
    if no_fallback and d.fallback_used:
        fails.append((label, f"fallback used where a typed relation was expected: {d.fallback_used}"))
    return d


def dx(label, obs, *, state=None, top=None, min_candidates=None, has_next_test=False):
    r = diagnose(obs)
    if state and r['state'] != state:
        fails.append((label, f"state {r['state']} != {state}"))
    if top and (not r['candidates'] or r['candidates'][0].cause != top):
        got = r['candidates'][0].cause if r['candidates'] else None
        fails.append((label, f"top {got} != {top}"))
    if min_candidates and len(r['candidates']) < min_candidates:
        fails.append((label, f"only {len(r['candidates'])} candidates, expected >= {min_candidates}"))
    if has_next_test and 'खात्री' not in r['message_mr'] and 'वेगळे करा' not in r['message_mr']:
        fails.append((label, "no next test offered on an uncertain diagnosis"))
    if state == 'CONFIRMED' and not r.get('treatment_rule'):
        fails.append((label, "confirmed but no treatment rule"))
    if state in ('AMBIGUOUS', 'PROBABLE') and r.get('treatment_rule'):
        fails.append((label, "treatment offered on an unconfirmed diagnosis"))
    return r


print("═══ PRECEDENCE ═══\n")

# --- the case that severity alone gets wrong -------------------------------
case("उष्णतेत फवारणी दडपली",
     [('D04-MC-001','yellow',5,0.11), ('D04-MC-004','info',3)],
     issued=['D04-MC-004'], suppressed_ids=['D04-MC-001'])

case("थंड हवामानात फवारणी होते",
     [('D04-MC-001','yellow',5,0.11)],
     issued=['D04-MC-001'], suppressed_ids=[])

# --- sensor beats computation ---------------------------------------------
case("संपृक्तता गणिताला ओलांडते",
     [('D03-WR-001','info',5), ('D03-MN-002','red',5)],
     issued=['D03-MN-002'], suppressed_ids=['D03-WR-001'])

case("संपृक्तता नसेल तर तक्ता चालतो",
     [('D03-WR-001','info',5)],
     issued=['D03-WR-001'], suppressed_ids=[])

# --- one event, one alert --------------------------------------------------
case("साचलेले पाणी — एकच इशारा, तीव्रता वाढवून",
     [('D03-WL-001','red',5,0.35), ('D03-WL-002','red',5), ('D06-SR-001','red',5,0.70)],
     escalated_into=['D03-WL-002','D06-SR-001'])

case("चक्रीवादळ — तीन Domain, एक इशारा",
     [('D03-WL-003','red',5,0.30), ('D07-CY-001','red',5,0.30)],
     issued=['D07-CY-001'], suppressed_ids=['D03-WL-003'])

case("PHI — तीन नियम, एक अडथळा",
     [('D05-CH-003','blocking',5), ('D06-CH-003','blocking',5)],
     issued=['D06-CH-003'], suppressed_ids=['D05-CH-003'])

case("वाफसा — दोन Domain, एक सूचना",
     [('D02-TL-003','info',3), ('D08-TL-002','info',3)],
     issued=['D08-TL-002'], suppressed_ids=['D02-TL-003'])

# --- disease stops nutrition ----------------------------------------------
case("रोग आढळल्यावर खत थांबते",
     [('D04-NS-001','yellow',4,0.10), ('D04-PK-001','yellow',5,0.12), ('D04-DG-003','red',5)],
     issued=['D04-DG-003'], suppressed_ids=['D04-NS-001','D04-PK-001'])

case("मर रोगावर कंदकुजीचा उपचार दाखवला जात नाही",
     [('D06-DX-003','red',5,0.70), ('D06-CH-001','blocking',5)],
     issued=['D06-CH-001'], suppressed_ids=['D06-DX-003'])

# --- window closed ---------------------------------------------------------
case("फुलोरा आल्यावर उटाळणी सुचवली जात नाही",
     [('D08-EU-001','yellow',5,0.125), ('D08-EU-002','red',5,0.125)],
     issued=['D08-EU-002'], suppressed_ids=['D08-EU-001'])

# --- sequencing ------------------------------------------------------------
case("निदानापूर्वी नत्र नाही",
     [('D04-DG-001','red',5), ('D04-NS-001','yellow',4,0.10)],
     issued=['D04-DG-001'], waits=['D04-NS-001'])

d = P.resolve([Fired('D04-DG-001','red',5), Fired('D04-NS-001','yellow',4,0.10)])
d2 = P.resolve([Fired('D04-DG-001','red',5), Fired('D04-NS-001','yellow',4,0.10)],
               answered={'D04-DG-001'})
if 'D04-NS-001' not in d2.issued:
    fails.append(("निदान झाल्यावर नत्र सुटतो", f"issued {d2.issued}"))

# --- bundling --------------------------------------------------------------
case("Bundle 3 — एक फेरी",
     [('D08-EU-001','yellow',5,0.125), ('D04-NS-002','yellow',5),
      ('D08-MU-002','yellow',4), ('D08-EU-005','yellow',5)],
     issued=['D08-EU-001'],
     bundled={'D08-EU-001': ['D04-NS-002','D08-MU-002','D08-EU-005']})

# --- specific beats general ------------------------------------------------
case("G3 मध्ये ७ दिवसांचा नियम, १० चा नाही",
     [('D03-MN-003','yellow',4), ('D03-MN-004','red',5,0.20)],
     issued=['D03-MN-004'], suppressed_ids=['D03-MN-003'])

case("२०० दिवसांआधी पक्वता नाकारली",
     [('D09-MT-001','info',5,0.12), ('D09-MT-002','red',5)],
     issued=['D09-MT-002'], suppressed_ids=['D09-MT-001'])

# --- no relation: fallback should be recorded, not silent ------------------
d = P.resolve([Fired('D07-RF-001','red',5), Fired('D10-SUB-002','blocking',5)])
if not d.fallback_used:
    fails.append(("संबंध नसताना fallback नोंदवला जातो", "fallback_used रिकामे"))

print(f"  {len(PRECEDENCE)} typed relations, {len(RELATIONS)} प्रकार")

print("\n═══ MULTI-DIAGNOSIS ═══\n")

dx("दुधाळ धागा -> मर रोग निश्चित",
   {'ooze_test_result':'milky_thread'}, state='CONFIRMED', top='bacterial_wilt')

dx("सुरळी मेली -> कंदकूज निश्चित",
   {'central_shoot_dead':True}, state='CONFIRMED', top='soft_rot')

dx("नव्या पानांत शिरांमधील पिवळे + चुनखडी",
   {'leaf_yellowing_pattern':'interveinal_new','soil_free_lime_present':True},
   state='PROBABLE', top='iron_zinc_lockup', has_next_test=True)

dx("जुनी पानं पिवळी -> नत्र, लोह वगळले",
   {'leaf_yellowing_pattern':'uniform_old'}, top='nitrogen_deficiency')

# the case the whole feature exists for
r = dx("कडा करपल्या + माती ओली -> दोन शक्यता",
       {'leaf_yellowing_pattern':'margin_scorch','soil_moisture_saturated':True},
       min_candidates=2, has_next_test=True)
if r['state'] == 'CONFIRMED':
    fails.append(("दोन शक्यता", "CONFIRMED दिले, पण निर्णायक खूण नाही"))

dx("काहीच नोंद नाही -> उपचार नाही", {}, state='NO_CANDIDATE')

# exclusion must actually exclude
r = diagnose({'ooze_test_result':'milky_thread','rhizome_smell':'sour_foul'})
if any(c.cause == 'soft_rot' for c in r['candidates']):
    fails.append(("दुधाळ धागा असताना कूज वगळली जाते",
                  f"candidates {[c.cause for c in r['candidates']]}"))

# a confirmed diagnosis must not be outranked by a weakly supported one
r = diagnose({'central_shoot_dead':True,'soil_moisture_saturated':True,
              'air_temp_above_35_3d':True,'leaf_yellowing_pattern':'margin_scorch'})
if r['candidates'][0].cause != 'soft_rot':
    fails.append(("निर्णायक खूण इतर पुराव्यांवर वरचढ",
                  f"top {r['candidates'][0].cause}"))

print("\n═══ निकाल ═══\n")
if fails:
    for label, why in fails:
        print(f"  ❌ {label}")
        print(f"     {why}")
    print(f"\n  {len(fails)} अपयश")
    sys.exit(1)
print("  ✅ सर्व पास")
