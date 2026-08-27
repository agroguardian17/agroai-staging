#!/usr/bin/env python3
"""
AgroGuardian AI — Notification Policy
=====================================

The season simulation surfaced a design fault that no unit test could:
the engine issued 998 messages across 301 days, on every single day, with
two blocking rules repeating 301 and 226 times.

The cause is a category error. A trigger expresses a CONDITION, and a
condition stays true for as long as it is true. "Water supply is short" is
true every day from April until it is fixed. But the ADVICE is an event and
should be delivered once, then repeated only on a schedule that respects
what kind of advice it is.

Four delivery classes, derived from what the rule actually asks for:

  ONCE_UNTIL_RESOLVED   A standing precondition. Say it once. Repeat on an
                        escalating ladder — 7, 21, 45 days — and escalate the
                        severity rather than the frequency. D03-WS-001,
                        D02-CL-002, D10-SUB-002.

  EVENT                 A transient physical event. Deliver on the rising
                        edge; do not repeat while it persists; re-arm once
                        it has cleared for a day. D03-WL-001, D07-CY-001.

  WINDOW                A dated operation. Advance warning, the day itself,
                        then a limited number of overdue reminders before the
                        window is recorded as missed. D08-EU-001, D04-MC-001.

  SILENT_GUARD          A rule whose whole purpose is to prevent something.
                        It produces NO farmer message unless the prohibited
                        action is actually attempted. D08-WD-001 blocks a
                        herbicide the farmer is not applying today; telling
                        him daily is noise. D04-SB-001, D06-CH-001, D12-*.

The last class is the important one. 226 of the daily messages came from a
rule that exists to stop a herbicide, fired on a day nobody was spraying.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

ONCE_UNTIL_RESOLVED = 'ONCE_UNTIL_RESOLVED'
EVENT               = 'EVENT'
WINDOW              = 'WINDOW'
SILENT_GUARD        = 'SILENT_GUARD'

# Reminder ladder for standing preconditions, in days since first issue.
LADDER = (0, 7, 21, 45, 90)

# Overdue reminders for a dated operation before it is recorded as missed.
WINDOW_OVERDUE_REMINDERS = 3


DELIVERY = {

 # --- silent guards: no message unless the prohibited action is attempted --
 'D08-WD-001': SILENT_GUARD,   # herbicide after emergence
 'D08-GR-003': SILENT_GUARD,   # brand name proposed
 'D04-SB-001': SILENT_GUARD,   # dose from probe
 'D04-NP-002': SILENT_GUARD,   # dose from inflated target
 'D04-NS-003': SILENT_GUARD,   # nitrogen after 80 DAP
 'D05-CH-001': SILENT_GUARD,   # blocklisted molecule
 'D05-CH-003': SILENT_GUARD,   # PHI unknown
 'D06-CH-001': SILENT_GUARD,   # fungicide on bacterial wilt
 'D06-CH-003': SILENT_GUARD,
 'D09-SF-001': SILENT_GUARD,   # PPE absent
 'D09-SF-002': SILENT_GUARD,
 'D09-PR-001': SILENT_GUARD,   # caustic method requested
 'D09-PR-002': SILENT_GUARD,
 'D05-TC-002': SILENT_GUARD,   # wilt host intercrop chosen
 'D08-IC-001': SILENT_GUARD,
 'D13-RP-002': SILENT_GUARD,   # seed retention from infected plot
 'D13-AD-002': SILENT_GUARD,   # profit guarantee
 'D12-POS-001': SILENT_GUARD,
 'D12-POS-003': SILENT_GUARD,
 'D12-DPDP-001': SILENT_GUARD,
 'D12-DPDP-002': SILENT_GUARD,
 'D12-DPDP-003': SILENT_GUARD,
 'D10-FRESH-002': SILENT_GUARD,
 'D13-RV-001': SILENT_GUARD,   # price shown without break-even
 'D13-SRC-001': SILENT_GUARD,
 'D13-SD-002': SILENT_GUARD,
 'D01-HV-002': SILENT_GUARD,   # maturity conclusion attempted early
 'D09-MT-002': SILENT_GUARD,
 'D04-DG-003': SILENT_GUARD,   # nutrient advisory during disease
 'D06-DX-002': SILENT_GUARD,   # fungicide path on wilt
 'D08-EU-002': SILENT_GUARD,   # earthing up attempted after flowering

 # --- standing preconditions: say once, escalate slowly -------------------
 'D03-WS-001': ONCE_UNTIL_RESOLVED,
 'D02-CL-002': ONCE_UNTIL_RESOLVED,
 'D03-DS-003': ONCE_UNTIL_RESOLVED,
 'D02-DR-001': ONCE_UNTIL_RESOLVED,
 'D02-DR-002': ONCE_UNTIL_RESOLVED,
 'D01-HW-001': ONCE_UNTIL_RESOLVED,
 'D03-SB-001': ONCE_UNTIL_RESOLVED,
 'D08-LY-001': ONCE_UNTIL_RESOLVED,
 'D07-RF-001': ONCE_UNTIL_RESOLVED,
 'D10-SUB-002': ONCE_UNTIL_RESOLVED,
 'D01-PW-001': ONCE_UNTIL_RESOLVED,
 'D09-GD-002': ONCE_UNTIL_RESOLVED,

 # --- transient events: rising edge only ----------------------------------
 'D03-WL-001': EVENT,
 'D03-WL-002': EVENT,
 'D03-WL-003': EVENT,
 'D07-CY-001': EVENT,
 'D06-SR-001': EVENT,
 'D03-MN-002': EVENT,
 'D03-MN-004': EVENT,
 'D07-MO-002': EVENT,
 'D02-CA-002': EVENT,

 # --- G4 dated operations, added after the simulation found the silence ---
 'D04-PK-001': WINDOW,
 'D04-PK-002': WINDOW,
 'D08-EU-004': WINDOW,
 'D08-MU-002': WINDOW,
 'D09-WW-001': WINDOW,
 'D03-SC-006': ONCE_UNTIL_RESOLVED,

 # --- wave 2 ---------------------------------------------------------------
 'D04-MC-004': SILENT_GUARD,   # suppressor, never a message of its own
 'D07-HS-004': SILENT_GUARD,
 'D08-GF-001': SILENT_GUARD,   # only when gap filling is attempted
 'D09-WW-002': SILENT_GUARD,
 'D04-NU-002': SILENT_GUARD,
 'D01-TM-002': SILENT_GUARD,

 'D03-WR-001': SILENT_GUARD,   # the engine computes; it does not announce
 'D03-WR-002': SILENT_GUARD,
 'D03-SB-002': ONCE_UNTIL_RESOLVED,
 'D07-CC-001': ONCE_UNTIL_RESOLVED,
 'D10-INS-001': ONCE_UNTIL_RESOLVED,
 'D13-RR-001': ONCE_UNTIL_RESOLVED,
 'D08-CA-001': ONCE_UNTIL_RESOLVED,
 'D09-YD-001': ONCE_UNTIL_RESOLVED,
 'D09-PH-001': ONCE_UNTIL_RESOLVED,
 'D05-SC-001': ONCE_UNTIL_RESOLVED,
 'D04-SB-002': ONCE_UNTIL_RESOLVED,

 'D03-MN-001': SILENT_GUARD,   # daily arithmetic, not an advisory
 'D02-DR-003': EVENT,
 'D05-SW-001': EVENT,
 'D07-HU-001': EVENT,
 'D06-LS-001': EVENT,
 'D06-DX-005': EVENT,
 'D05-WG-002': EVENT,
 'D05-NE-001': EVENT,
 'D04-SB-003': EVENT,
 'D03-SC-002': EVENT,
 'D08-EU-005': EVENT,
 'D02-TL-003': EVENT,
 'D08-TL-002': EVENT,
 'D03-SC-003': EVENT,
 'D07-CY-002': EVENT,

 # --- wave 3 ---------------------------------------------------------------
 # suppressors and internal computations: never a message of their own
 'D05-CH-006': SILENT_GUARD,
 'D03-SC-001': SILENT_GUARD, 'D07-RF-005': SILENT_GUARD,
 'D07-BC-001': SILENT_GUARD, 'D07-BC-002': SILENT_GUARD, 'D07-BC-003': SILENT_GUARD,
 'D01-PH-001': SILENT_GUARD, 'D01-PH-003': SILENT_GUARD, 'D01-HV-004': SILENT_GUARD,
 'D01-TM-001': EVENT,
 'D09-MT-003': SILENT_GUARD, 'D09-ST-003': SILENT_GUARD, 'D05-CH-005': SILENT_GUARD,
 'D06-CH-004': SILENT_GUARD, 'D04-DG-004': SILENT_GUARD, 'D08-BN-001': SILENT_GUARD,
 'D07-CL-002': SILENT_GUARD, 'D07-CC-003': SILENT_GUARD, 'D13-RR-002': SILENT_GUARD,
 'D03-MU-001': SILENT_GUARD, 'D07-TM-001': EVENT, 'D07-HS-001': EVENT,
 'D05-PC-002': SILENT_GUARD, 'D07-HU-003': SILENT_GUARD, 'D07-HU-004': SILENT_GUARD,

 # transient weather and field events
 'D03-WR-003': EVENT, 'D03-WR-004': EVENT, 'D03-WL-004': EVENT, 'D03-MN-003': EVENT,
 'D07-TM-002': EVENT, 'D07-TM-003': EVENT, 'D07-HS-002': EVENT, 'D07-HS-003': EVENT,
 'D07-RF-003': EVENT, 'D07-MO-003': EVENT, 'D07-MO-004': EVENT, 'D07-HU-002': EVENT,
 'D07-WS-001': EVENT, 'D07-WS-002': EVENT, 'D07-WS-003': EVENT, 'D07-WS-004': EVENT,
 'D07-RF-002': EVENT, 'D07-RF-004': EVENT, 'D05-LR-001': EVENT, 'D06-SW-001': EVENT,
 'D06-SW-002': EVENT, 'D06-SW-003': EVENT, 'D08-IC-003': EVENT, 'D09-HV-004': EVENT,

 # standing preconditions
 'D01-VR-001': ONCE_UNTIL_RESOLVED, 'D03-DS-001': ONCE_UNTIL_RESOLVED,
 'D03-DS-002': ONCE_UNTIL_RESOLVED, 'D04-FG-001': ONCE_UNTIL_RESOLVED,
 'D04-SN-002': ONCE_UNTIL_RESOLVED, 'D05-PC-004': ONCE_UNTIL_RESOLVED,
 'D13-RR-004': ONCE_UNTIL_RESOLVED, 'D01-HV-001': ONCE_UNTIL_RESOLVED,
 'D03-SC-004': ONCE_UNTIL_RESOLVED, 'D08-LB-001': ONCE_UNTIL_RESOLVED,
 'D04-DG-001': EVENT,
 'D06-DX-001': EVENT,
 'D04-FG-002': EVENT,
}

DEFAULT_DELIVERY = WINDOW


@dataclass
class Issue:
    rule_id: str
    day: date
    kind: str
    reason: str
    escalation: int = 0        # 0 = first issue, 1+ = ladder step
    severity_bump: int = 0     # steps to raise severity by


class Notifier:
    """Decides whether a fired rule actually reaches the farmer today."""

    def __init__(self, delivery=None):
        self.delivery = dict(DELIVERY) if delivery is None else dict(delivery)
        self.first_issued: dict[str, date] = {}
        self.last_issued: dict[str, date] = {}
        self.issue_count: dict[str, int] = defaultdict(int)
        self.active: set[str] = set()          # for EVENT edge detection
        self.resolved: set[str] = set()
        self.window_overdue: dict[str, int] = defaultdict(int)
        self.suppressed_by_policy: dict[str, int] = defaultdict(int)

    def kind(self, rule_id): return self.delivery.get(rule_id, DEFAULT_DELIVERY)

    def clear(self, rule_id, day):
        """Called when a rule no longer fires — re-arms EVENT rules."""
        if rule_id in self.active:
            self.active.discard(rule_id)

    def resolve(self, rule_id):
        """Called when the underlying condition is genuinely fixed."""
        self.resolved.add(rule_id)

    def decide(self, rule_id, day: date, action_attempted: bool = False) -> Issue | None:
        k = self.kind(rule_id)

        if k == SILENT_GUARD:
            if action_attempted:
                self._record(rule_id, day)
                return Issue(rule_id, day, k, 'प्रतिबंधित कृती करण्याचा प्रयत्न')
            self.suppressed_by_policy[rule_id] += 1
            return None

        if k == EVENT:
            if rule_id in self.active:
                self.suppressed_by_policy[rule_id] += 1
                return None                      # already reported, still true
            self.active.add(rule_id)
            self._record(rule_id, day)
            return Issue(rule_id, day, k, 'नवीन घटना')

        if k == ONCE_UNTIL_RESOLVED:
            if rule_id in self.resolved:
                self.suppressed_by_policy[rule_id] += 1
                return None
            first = self.first_issued.get(rule_id)
            if first is None:
                self._record(rule_id, day)
                return Issue(rule_id, day, k, 'प्रथम सूचना')
            elapsed = (day - first).days
            step = self.issue_count[rule_id]
            if step < len(LADDER) and elapsed >= LADDER[step]:
                self._record(rule_id, day)
                return Issue(rule_id, day, k,
                             f'स्मरण {step} — {elapsed} दिवसांपासून प्रलंबित',
                             escalation=step, severity_bump=min(step, 2))
            self.suppressed_by_policy[rule_id] += 1
            return None

        # WINDOW
        last = self.last_issued.get(rule_id)
        if last is None:
            self._record(rule_id, day)
            return Issue(rule_id, day, k, 'खिडकी उघडली')
        if (day - last).days >= 3:
            self.window_overdue[rule_id] += 1
            if self.window_overdue[rule_id] <= WINDOW_OVERDUE_REMINDERS:
                self._record(rule_id, day)
                return Issue(rule_id, day, k,
                             f'प्रलंबित स्मरण {self.window_overdue[rule_id]}',
                             escalation=self.window_overdue[rule_id])
        self.suppressed_by_policy[rule_id] += 1
        return None

    def _record(self, rule_id, day):
        self.first_issued.setdefault(rule_id, day)
        self.last_issued[rule_id] = day
        self.issue_count[rule_id] += 1


def coverage_report(compiled_ids):
    """Which rules have an explicit delivery class and which fall to default."""
    explicit = [r for r in compiled_ids if r in DELIVERY]
    default = [r for r in compiled_ids if r not in DELIVERY]
    from collections import Counter
    return dict(
        explicit=len(explicit),
        default=len(default),
        by_kind=dict(Counter(DELIVERY[r] for r in explicit)),
        defaulted=sorted(default),
    )
