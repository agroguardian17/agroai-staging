#!/usr/bin/env python3
"""
AgroGuardian AI — Expert Override
=================================

The Tier-1 review changed six rules. That worked, but it was offline: I edited
the JSON and regenerated. An agronomist looking at a live plot in August cannot
do that, and by the time a code change ships the window has closed.

So this is the runtime path. An authorised expert adjusts rule behaviour
without a deploy, and every adjustment is scoped, dated, attributed and
reversible.

WHAT AN OVERRIDE CAN DO
-----------------------
    THRESHOLD    change a number inside the trigger expression
    DELIVERY     change how often the advice is issued
    SEVERITY     raise or lower urgency
    DISABLE      stop a rule firing for a scope and a period
    PARAMETER    change a quantity inside the action text

WHAT IT CAN NEVER DO
--------------------
Some rules exist because getting them wrong causes harm that no agronomic
judgement outweighs. These carry immutable=True and the override API refuses
them outright — not by policy, by the code path.

    - a banned molecule stays banned                    D05-CH-001
    - no fungicide is offered for bacterial wilt        D06-CH-001
    - caustic processing needs PPE and training         D09-SF-001
    - pre-harvest intervals are observed                D05/D06/D09 PHI
    - consent is obtained before data is collected      D12-DPDP-001/002
    - coordinates are coarsened before sharing          D12-DPDP-003
    - capability claims stay accurate                   D12-POS-001/003

An expert who disagrees with one of these is not making an agronomic call.
The right response is to escalate to a knowledge base revision with a written
rationale, which is a different and slower process on purpose.

SCOPE AND EXPIRY
----------------
Every override is scoped — one plot, one cluster, or global — and every
override expires. A permanent change belongs in the knowledge base, not in
the override table. The default expiry is one season.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, timedelta

# ---------------------------------------------------------------------------
# The immutable core. Declared, not inferred.
# ---------------------------------------------------------------------------

IMMUTABLE = {
    # banned and restricted molecules
    'D05-CH-001': 'BHC and monocrotophos are banned or restricted. No agronomic judgement changes that.',
    # bacterial wilt has no fungicide answer
    'D06-CH-001': 'No fungicide has activity against a bacterium. Offering one wastes money while the pathogen spreads.',
    'D06-DX-002': 'The wilt diagnosis gates the fungicide path. Overriding it reopens the path.',
    # pre-harvest intervals
    'D05-CH-003': 'Residue on a harvested rhizome is a food safety matter, not an agronomic preference.',
    'D06-CH-003': 'Same.',
    'D09-SF-002': 'Same, at the harvest decision rather than the spray decision.',
    # operator safety
    'D09-SF-001': 'Boiling caustic soda causes permanent injury. PPE and training are not negotiable.',
    'D09-PR-001': 'The safety warning must precede the method, always.',
    'D09-PR-002': 'SO2 residue limits are unverified. Until they are, this method is not first choice.',
    # data protection
    'D12-DPDP-001': 'Consent before collection is a legal requirement.',
    'D12-DPDP-002': 'Separate consent for data sharing is a legal requirement.',
    'D12-DPDP-003': 'GPS coordinates cannot be anonymised. Coarsening is the only compliant path.',
    # honest capability claims
    'D12-POS-001': 'Describing the system accurately is a commercial and regulatory obligation.',
    'D12-POS-003': 'Prohibited capability claims stay prohibited.',
    # brand independence
    'D08-GR-003': 'Naming a commercial brand creates a conflict the platform cannot carry.',
    # profit guarantees
    'D13-AD-002': 'The engine does not guarantee profit or forecast prices.',
}

OVERRIDE_KINDS = ('THRESHOLD', 'DELIVERY', 'SEVERITY', 'DISABLE', 'PARAMETER')
SCOPES = ('plot', 'cluster', 'global')
SEVERITIES = ('info', 'yellow', 'red', 'blocking')
DELIVERIES = ('ONCE_UNTIL_RESOLVED', 'EVENT', 'WINDOW', 'SILENT_GUARD')

DEFAULT_EXPIRY_DAYS = 240          # one season
MAX_EXPIRY_DAYS = 400


class OverrideRefused(Exception):  # noqa: N818 - public engine name used by callers
    """Raised when an override is not permitted. The message is farmer-facing safe."""


@dataclass
class Override:
    override_id: str
    rule_id: str
    kind: str
    scope: str
    scope_id: str | None          # plot_id / cluster_id, None for global
    expert_id: str
    expert_name: str
    rationale_mr: str
    created: date
    expires: date
    # payload, one of:
    new_threshold: dict | None = None      # {'from': 12, 'to': 9}
    new_delivery: str | None = None
    new_severity: str | None = None
    new_parameter: dict | None = None      # {'name':'cost_mulch','from':15000,'to':11000}
    disable_reason_mr: str | None = None
    revoked: date | None = None
    revoked_by: str | None = None
    applied_count: int = 0

    @property
    def active(self):
        return self.revoked is None

    def in_force(self, day: date):
        return self.active and self.created <= day <= self.expires

    def applies_to(self, plot_id=None, cluster_id=None):
        if self.scope == 'global':
            return True
        if self.scope == 'plot':
            return self.scope_id == plot_id
        if self.scope == 'cluster':
            return self.scope_id == cluster_id
        return False


class OverrideStore:
    def __init__(self, rules: dict):
        self.rules = rules                      # rule_id -> rule dict
        self.items: list[Override] = []
        self.audit: list[dict] = []
        self._seq = 0

    # -- creation ----------------------------------------------------------
    def create(self, rule_id, kind, expert_id, expert_name, rationale_mr,
               scope='plot', scope_id=None, day=None, expiry_days=DEFAULT_EXPIRY_DAYS,
               **payload) -> Override:

        day = day or date.today()

        if rule_id not in self.rules:
            raise OverrideRefused(f"नियम अस्तित्वात नाही: {rule_id}")

        if rule_id in IMMUTABLE:
            self._log('REFUSED', rule_id, expert_id, IMMUTABLE[rule_id])
            raise OverrideRefused(
                f"{rule_id} बदलता येत नाही. {IMMUTABLE[rule_id]} "
                "असहमत असल्यास लेखी कारणासह knowledge base सुधारणा प्रस्तावित करा.")

        if kind not in OVERRIDE_KINDS:
            raise OverrideRefused(f"अज्ञात प्रकार: {kind}")
        if scope not in SCOPES:
            raise OverrideRefused(f"अज्ञात व्याप्ती: {scope}")
        if scope in ('plot', 'cluster') and not scope_id:
            raise OverrideRefused(f"{scope} व्याप्तीसाठी ओळख आवश्यक")
        if len((rationale_mr or '').strip()) < 15:
            raise OverrideRefused("कारण लिहिणे आवश्यक — किमान एक वाक्य")
        if expiry_days > MAX_EXPIRY_DAYS:
            raise OverrideRefused(
                f"{expiry_days} दिवस खूप जास्त. कायमस्वरूपी बदल override नाही — "
                "तो knowledge base सुधारणा आहे.")

        rule = self.rules[rule_id]

        # kind-specific validation
        if kind == 'SEVERITY':
            ns = payload.get('new_severity')
            if ns not in SEVERITIES:
                raise OverrideRefused(f"अज्ञात तीव्रता: {ns}")
            if rule['severity'] == 'blocking' and ns != 'blocking':
                raise OverrideRefused(
                    f"{rule_id} blocking आहे. तीव्रता कमी करण्याऐवजी DISABLE वापरा — "
                    "म्हणजे नोंद स्पष्ट राहील.")

        if kind == 'DELIVERY':
            nd = payload.get('new_delivery')
            if nd not in DELIVERIES:
                raise OverrideRefused(f"अज्ञात वितरण वर्ग: {nd}")

        if kind == 'THRESHOLD':
            t = payload.get('new_threshold') or {}
            if 'from' not in t or 'to' not in t:
                raise OverrideRefused("threshold override ला from आणि to दोन्ही हवेत")
            expr = rule.get('trigger', {}).get('expr', '')
            if str(t['from']) not in expr:
                raise OverrideRefused(
                    f"मूल्य {t['from']} या नियमाच्या अटीत सापडत नाही. "
                    "override प्रत्यक्ष अटीशी जुळले पाहिजे.")
            # a threshold move that weakens a red or blocking rule needs a bigger
            # justification, so require the rationale to be longer
            if rule['severity'] in ('red', 'blocking') and len(rationale_mr.strip()) < 40:
                raise OverrideRefused(
                    f"{rule_id} ची तीव्रता {rule['severity']} आहे. "
                    "मर्यादा बदलण्यासाठी सविस्तर कारण आवश्यक.")

        if kind == 'DISABLE':
            if not payload.get('disable_reason_mr'):
                raise OverrideRefused("DISABLE साठी वेगळे कारण आवश्यक")
            if rule['severity'] == 'blocking' and scope == 'global':
                raise OverrideRefused(
                    f"{rule_id} blocking आहे. जागतिक पातळीवर बंद करता येत नाही — "
                    "प्लॉट किंवा cluster पुरते मर्यादित करा.")

        self._seq += 1
        ov = Override(
            override_id=f"OV-{day.isoformat()}-{self._seq:04d}",
            rule_id=rule_id, kind=kind, scope=scope, scope_id=scope_id,
            expert_id=expert_id, expert_name=expert_name, rationale_mr=rationale_mr,
            created=day, expires=day + timedelta(days=expiry_days),
            new_threshold=payload.get('new_threshold'),
            new_delivery=payload.get('new_delivery'),
            new_severity=payload.get('new_severity'),
            new_parameter=payload.get('new_parameter'),
            disable_reason_mr=payload.get('disable_reason_mr'),
        )
        self.items.append(ov)
        self._log('CREATED', rule_id, expert_id,
                  f"{kind} scope={scope}:{scope_id} expires={ov.expires}")
        return ov

    def revoke(self, override_id, expert_id, day=None):
        day = day or date.today()
        for ov in self.items:
            if ov.override_id == override_id and ov.active:
                ov.revoked = day
                ov.revoked_by = expert_id
                self._log('REVOKED', ov.rule_id, expert_id, override_id)
                return ov
        raise OverrideRefused(f"override सापडला नाही किंवा आधीच मागे घेतला: {override_id}")

    def _log(self, action, rule_id, expert_id, detail):
        self.audit.append(dict(action=action, rule_id=rule_id, expert_id=expert_id,
                               detail=detail, at=date.today().isoformat()))

    # -- application -------------------------------------------------------
    def effective(self, rule_id, day: date, plot_id=None, cluster_id=None) -> dict:
        """Return the rule as it should be applied today, plus what changed."""
        rule = self.rules[rule_id]
        out = dict(rule_id=rule_id,
                   severity=rule['severity'],
                   delivery=rule.get('delivery'),
                   expr=rule.get('trigger', {}).get('expr'),
                   disabled=False,
                   overrides=[])

        # narrowest scope wins: plot over cluster over global
        rank = {'plot': 0, 'cluster': 1, 'global': 2}
        applicable = [o for o in self.items
                      if o.rule_id == rule_id and o.in_force(day)
                      and o.applies_to(plot_id, cluster_id)]
        applicable.sort(key=lambda o: (rank[o.scope], -o.created.toordinal()))

        seen_kinds = set()
        for ov in applicable:
            if ov.kind in seen_kinds:
                continue                      # narrower scope already handled this kind
            seen_kinds.add(ov.kind)
            ov.applied_count += 1
            if ov.kind == 'DISABLE':
                out['disabled'] = True
            elif ov.kind == 'SEVERITY':
                out['severity'] = ov.new_severity
            elif ov.kind == 'DELIVERY':
                out['delivery'] = ov.new_delivery
            elif ov.kind == 'THRESHOLD' and out['expr']:
                out['expr'] = re.sub(rf"\b{re.escape(str(ov.new_threshold['from']))}\b",
                                     str(ov.new_threshold['to']), out['expr'], count=1)
            out['overrides'].append(dict(id=ov.override_id, kind=ov.kind, scope=ov.scope,
                                         by=ov.expert_name, rationale=ov.rationale_mr,
                                         expires=ov.expires.isoformat()))
        return out

    # -- reporting ---------------------------------------------------------
    def report(self, day=None):
        day = day or date.today()
        live = [o for o in self.items if o.in_force(day)]
        expiring = [o for o in live if (o.expires - day).days <= 30]
        unused = [o for o in live if o.applied_count == 0]
        return dict(total=len(self.items), live=len(live),
                    expiring_soon=len(expiring), never_applied=len(unused),
                    by_kind={k: sum(1 for o in live if o.kind == k) for k in OVERRIDE_KINDS},
                    by_scope={s: sum(1 for o in live if o.scope == s) for s in SCOPES},
                    refused=sum(1 for a in self.audit if a['action'] == 'REFUSED'))


def load_rules():
    from pathlib import Path
    files = ['Domain1_Rules_Ginger_v2.json'] + [f'Domain{i}_Rules_Ginger.json' for i in range(2, 14)]
    rules = {}
    for fn in files:
        d = json.loads(Path(fn).read_text(encoding='utf-8'))
        for r in d['rules']:
            rules[r['rule_id']] = r
    return rules


if __name__ == '__main__':
    rules = load_rules()
    st = OverrideStore(rules)
    today = date(2026, 8, 15)

    print("═══ स्वीकारलेले override ═══\n")

    ov = st.create('D02-DR-001', 'THRESHOLD', 'AG-001', 'डॉ. कदम',
                   'या भागातील काळी जमीन जास्त खोल आहे आणि खालचा थर वालुकामय आहे. '
                   'बारा तासांची मर्यादा इथे कडक ठरते; नऊ तास अधिक योग्य.',
                   scope='cluster', scope_id='KND-01', day=today,
                   new_threshold={'from': 12, 'to': 9})
    print(f"  ✅ {ov.override_id}  {ov.rule_id}  {ov.kind}  {ov.scope}:{ov.scope_id}")
    eff = st.effective('D02-DR-001', today, cluster_id='KND-01')
    print(f"     अट आता: {eff['expr'][:88]}...")

    ov2 = st.create('D04-MC-001', 'DELIVERY', 'AG-001', 'डॉ. कदम',
                    'या शेतकऱ्याला दर तीन दिवसांनी स्मरण उपयोगी पडते.',
                    scope='plot', scope_id='PLOT-77', day=today,
                    new_delivery='WINDOW')
    print(f"  ✅ {ov2.override_id}  {ov2.rule_id}  {ov2.kind}")

    ov3 = st.create('D05-SW-001', 'DISABLE', 'AG-002', 'डॉ. माळी',
                    'या cluster मध्ये प्रकाश सापळ्याची नोंद चालू आहे, त्यामुळे हा इशारा दुहेरी ठरतो.',
                    scope='cluster', scope_id='KND-01', day=today,
                    disable_reason_mr='दुहेरी इशारा')
    print(f"  ✅ {ov3.override_id}  {ov3.rule_id}  DISABLE")

    print("\n═══ नाकारलेले override ═══\n")
    for rid, kind, _why, kw in [
        ('D05-CH-001','DISABLE','प्रतिबंधित रसायन',{'disable_reason_mr':'x'}),
        ('D06-CH-001','SEVERITY','मर रोगावर बुरशीनाशक',{'new_severity':'info'}),
        ('D12-DPDP-003','DISABLE','निर्देशांक',{'disable_reason_mr':'x'}),
        ('D09-SF-001','SEVERITY','PPE',{'new_severity':'info'}),
    ]:
        try:
            st.create(rid, kind, 'AG-001', 'डॉ. कदम',
                      'या भागात हे लागू होत नाही असे वाटते.', scope='global', day=today, **kw)
            print(f"  ❌ {rid} स्वीकारला — हे चुकीचे आहे")
        except OverrideRefused as e:
            print(f"  ✅ {rid} नाकारला")
            print(f"     {str(e)[:96]}...")

    print("\n═══ इतर संरक्षणे ═══\n")
    for label, fn in [
        ('कारण खूप छोटे', lambda: st.create('D03-WL-001','SEVERITY','AG-1','x','छोटे',
                                            scope='plot',scope_id='P1',day=today,new_severity='yellow')),
        ('कायमस्वरूपी override', lambda: st.create('D04-MC-002','DELIVERY','AG-1','x',
                                            'हा बदल कायमचा हवा आहे कारण इथे नेहमीच असे असते.',
                                            scope='plot',scope_id='P1',day=today,expiry_days=900,
                                            new_delivery='EVENT')),
        ('अटीत नसलेले मूल्य', lambda: st.create('D03-MN-004','THRESHOLD','AG-1','x',
                                            'सात दिवस इथे खूप कमी वाटतात, दहा योग्य ठरतील असे अनुभवावरून वाटते.',
                                            scope='plot',scope_id='P1',day=today,
                                            new_threshold={'from':99,'to':10})),
        ('blocking जागतिक बंद', lambda: st.create('D02-CL-002','DISABLE','AG-1','x',
                                            'या भागात ठिबकाशिवायही लागवड होते असे दिसते.',
                                            scope='global',day=today,disable_reason_mr='y')),
    ]:
        try:
            fn()
            print(f"  ❌ {label} स्वीकारला — चुकीचे")
        except OverrideRefused as e:
            print(f"  ✅ {label} नाकारला: {str(e)[:70]}...")

    print("\n═══ व्याप्तीचा क्रम ═══\n")
    st.create('D04-MC-001','DELIVERY','AG-003','डॉ. महाजन',
              'सर्व शेतांसाठी हा वर्ग बदलावा असे वाटते.',
              scope='global', day=today, new_delivery='EVENT')
    for pid, label in [('PLOT-77','plot override असलेले'), ('PLOT-99','फक्त global')]:
        e = st.effective('D04-MC-001', today, plot_id=pid)
        print(f"  {label:24s} -> delivery={e['delivery']:20s} ({len(e['overrides'])} override)")

    print("\n═══ स्थिती ═══\n")
    for k, v in st.report(today).items():
        print(f"  {k:16s} {v}")
