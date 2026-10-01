#!/usr/bin/env python3
"""
Wave 4 — VPD retrofit (Domain 7 only, additive).

Three triggers added under the new D07-VP category. Purpose is to give the
authoring surface (used by test_runtime_loader.py to compare against the
knowledge base) the same three expressions that Domain 7 now carries in JSON.

Runtime does not read this file — production loads rules from the database
(architecture §11A). This file exists so that regression_gate.py stops
reporting a build-vs-KB drift after the VPD patch.

Notes:
  - All three deliver as SILENT_GUARD; no message flood risk.
  - D07-VP-002 BUNDLES with D07-HS-004 — the same spray event, one message.
  - D07-VP-003 augments the leaf wetness estimate D07-HU-002 relies on; it
    does not raise a new disease alert and cannot silence any existing rule.
"""

T, F, U = 'TRUE', 'FALSE', 'UNKNOWN'

TRIGGERS_W4 = {

# ===========================================================================
# D07 — Weather & Climate — VPD (additive)
# ===========================================================================

'D07-VP-001': {
  'expr': "air_temp_max_c IS NOT NULL AND rh_pct IS NOT NULL",
  'note': (
    'Computation trigger. Produces vpd_kpa via Tetens; consumed by VP-002, '
    'VP-003 and any downstream rule that reads the field. Emits nothing to '
    'the farmer.'
  ),
  'tests': [
    ({'air_temp_max_c': 30, 'rh_pct': 60}, T, 'vpd गणना'),
    ({'air_temp_max_c': 30, 'rh_pct': None}, F, 'rh गहाळ — IS NOT NULL returns FALSE'),
    ({'air_temp_max_c': None, 'rh_pct': 60}, F, 'tapmaan गहाळ — IS NOT NULL returns FALSE'),
  ]},

'D07-VP-002': {
  'expr': "spray_scheduled_today IS TRUE AND (vpd_kpa < 0.4 OR vpd_kpa > 2.0)",
  'note': (
    'SILENT_GUARD. BUNDLES with D07-HS-004 — same spray event, one combined '
    'message. Do not silence D07-HS-004 by lowering severity; use DISABLE '
    'if ever needed.'
  ),
  'tests': [
    ({'spray_scheduled_today': True, 'vpd_kpa': 0.25}, T, 'खूप ओलसर — फवारणी टाळा'),
    ({'spray_scheduled_today': True, 'vpd_kpa': 2.4}, T, 'खूप कोरडे — फवारणी टाळा'),
    ({'spray_scheduled_today': True, 'vpd_kpa': 1.1}, F, 'योग्य खिडकी'),
    ({'spray_scheduled_today': False, 'vpd_kpa': 0.25}, F, 'फवारणीच नाही'),
    ({'spray_scheduled_today': True, 'vpd_kpa': None}, U, 'vpd गहाळ'),
  ]},

'D07-VP-003': {
  'expr': "vpd_night_mean_kpa < 0.3 AND fog_observed IS FALSE AND MONTH IN [DEC, JAN, FEB]",
  'note': (
    'SILENT_GUARD. Tags the estimated leaf_wetness_hours field with high '
    'dew-probability confidence. Interim substitute for the missing leaf '
    'wetness sensor (D07-OI-05); does not raise a new disease alert.'
  ),
  'tests': [
    ({'vpd_night_mean_kpa': 0.2, 'fog_observed': False, 'current_month': 1}, T,
     'थंड निरभ्र रात्र — दव अपेक्षित'),
    ({'vpd_night_mean_kpa': 0.2, 'fog_observed': True, 'current_month': 1}, F,
     'धुके नोंदले — HU-002 कडे सिग्नल आहे'),
    ({'vpd_night_mean_kpa': 0.6, 'fog_observed': False, 'current_month': 1}, F,
     'कोरडी रात्र'),
    ({'vpd_night_mean_kpa': 0.2, 'fog_observed': False, 'current_month': 7}, F,
     'मान्सून — वेगळा रोग हंगाम'),
  ]},

}


# ---------------------------------------------------------------------------
# For runtime_loader / test_runtime_loader drift-detection to pick these up
# in one merged dictionary, apply_review.py or the test harness must include
# TRIGGERS_W4 alongside TRIGGERS_W1..W3. The one-line addition is:
#
#     from triggers_wave4_vpd import TRIGGERS_W4
#     ALL_TRIGGERS.update(TRIGGERS_W4)
#
# (Same pattern as W1/W2/W3.)
# ---------------------------------------------------------------------------

# Precedence delta — one BUNDLES entry to add to precedence.py PRECEDENCE_GRAPH:
PRECEDENCE_ADDITIONS = [
    {
        'subject': 'D07-VP-002',
        'relation': 'BUNDLES',
        'object': 'D07-HS-004',
        'reason_en': (
            'Both guards fire on the same scheduled foliar spray event. '
            'One field visit, one message: list temperature or rain, VPD, '
            'and the next recommended window together.'
        ),
        'reason_mr': (
            'दोन्ही नियम एकाच फवारणी घटनेवर लागू होतात. एकाच शेतफेरीत एकच '
            'संदेश द्या — तापमान/पाऊस, VPD, आणि पुढील शिफारशीत वेळ एकत्र सांगा.'
        ),
    }
]

# Delivery-class delta — all three are SILENT_GUARD.
DELIVERY_ADDITIONS = {
    'D07-VP-001': 'SILENT_GUARD',
    'D07-VP-002': 'SILENT_GUARD',
    'D07-VP-003': 'SILENT_GUARD',
}

# Immutable delta — none.
IMMUTABLE_ADDITIONS = set()

if __name__ == '__main__':
    print(f'TRIGGERS_W4 defines {len(TRIGGERS_W4)} new triggers')
    for rid, spec in TRIGGERS_W4.items():
        print(f'  {rid}: {spec["expr"]}')
    print(f'PRECEDENCE_ADDITIONS: {len(PRECEDENCE_ADDITIONS)} relation(s)')
    print(f'DELIVERY_ADDITIONS: {len(DELIVERY_ADDITIONS)} rule(s)')
    print(f'IMMUTABLE_ADDITIONS: {len(IMMUTABLE_ADDITIONS)} rule(s)')
