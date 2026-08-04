#!/usr/bin/env python3
"""
AgroGuardian AI — Daily Advisory Runner
=======================================

The single entry point. Given a plot and a day, produce what the farmer reads.

Everything built so far has been validated in the abstract. The trigger tests
prove rules fire correctly, the precedence tests prove conflicts resolve, the
season simulation counts messages. None of them has looked at the message.

Domain 12 D12-LANG-002 specifies a four-part structure:

    what to do      one sentence, starting with a verb
    when            an exact date or deadline
    why             one sentence
    what if not     with a number wherever one exists

The fourth part is what creates urgency. "Do earthing up" is ignorable;
"do earthing up or lose 10 to 15 percent of the crop" is not. That is why
every rule carries u_value and yield_impact — so this part can be generated
rather than written by hand 431 times.

Pipeline
--------
    Farm Brain state
      -> evaluate triggers          (three-valued; UNKNOWN never fires)
      -> apply expert overrides     (narrowest scope wins)
      -> resolve precedence         (typed relations, not severity ranking)
      -> apply notification policy  (a condition is not an event)
      -> compose messages           (four parts, Marathi)
      -> order by priority score

The runner also reports what it could NOT decide and why, because
D12-COLD-001 requires the engine to degrade and say so rather than guess.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from trigger_dsl import TV, evaluate, parse

try:
    from triggers_wave1 import TRIGGERS as _W1
    from triggers_wave2 import TRIGGERS_W2 as _W2
    from triggers_wave3 import TRIGGERS_W3 as _W3
except ModuleNotFoundError:
    # The deployed backend loads trigger expressions from Postgres through
    # runtime_loader.build_runner(). The triggers_wave*.py files are upstream
    # authoring/build-time helpers, so they are optional in this checkout.
    _W1, _W2, _W3 = {}, {}, {}
from expert_override import OverrideStore
from notification_policy import Notifier
from precedence import Fired, Precedence, diagnose

TRIGGERS = {**_W1, **_W2, **_W3}
FILES = ['Domain1_Rules_Ginger_v2.json'] + [f'Domain{i}_Rules_Ginger.json' for i in range(2, 14)]
SYNTHETIC = {'current_month','days_to_planting','days_to_harvest','brand_name_proposed',
             'capability_claim_proposed','profit_guarantee_proposed','price_forecast_proposed'}

SEV_LABEL_MR = {'blocking': 'थांबा', 'red': 'तातडीचे', 'yellow': 'महत्त्वाचे', 'info': 'माहिती'}
SEV_ICON = {'blocking': '⛔', 'red': '🔴', 'yellow': '🟡', 'info': 'ℹ️'}  # noqa: RUF001
SEV_RANK = {'blocking': 0, 'red': 1, 'yellow': 2, 'info': 3}

# Rule actions are written for the engine as much as for the farmer. These
# rewrites turn the mechanism into the consequence.
ENGINE_TO_FARMER = [
    # specific rewrites first
    ('कीड-दाबाचा इशारा द्या आणि निरीक्षणाची वारंवारता दुप्पट करा',
     'या भागात कीड-दाब वाढला आहे. शेताची पाहणी नेहमीपेक्षा दुप्पट वेळा करा'),
    ('वजा ९० दिवसांपासून काढणीपर्यंतची कृती कालदर्शिका प्राधान्यक्रमासह द्या',
     'हंगामाची संपूर्ण कृती कालदर्शिका तयार आहे'),
    ('दहाही जोखमी परिणाम व उपायांसह मांडा, आणि पूर्णपणे टाळता येणाऱ्या चार वेगळ्या दाखवा',
     'हंगामातील दहा जोखमी नोंदवल्या आहेत. त्यातील चार पूर्णपणे टाळता येतात'),
    ('लाल इशारा —', 'तातडीचे —'),
    ('लाल इशारा द्या', 'तातडीने लक्ष द्या'),
    ('पूर्वसूचना द्या', 'पुढील दोन दिवसांची तयारी करा'),
    ('मासिक आठवण द्या', 'या महिन्यात एकदा तपासा'),
]

# Trailing engine directives. A rule action ends with instructions to the
# engine as often as to the farmer, and the farmer does not need them.
ENGINE_TAIL = re.compile(
    r'\s*(कारण सांगा[:：]?|हे वापरकर्त्याला सांगा\.?|स्पष्ट सांगा[:：]?|'  # noqa: RUF001
    r'नोंदवा आणि सांगा\.?|आणि ते सांगा\.?)\s*')

# Verbs addressed to the engine rather than to the farmer.
ENGINE_VERB = re.compile(
    r'(इशारा द्या|सूचना द्या|यादी द्या|मांडा|दाखवा|नोंदवा आणि)\b')


# ---------------------------------------------------------------------------
# Message composition
# ---------------------------------------------------------------------------

# Rules whose u_value belongs to a duplication group must not restate the loss,
# or the same number appears three times in one day's advisory.
def _loss_sentence(rule, action_text: str) -> str | None:
    u = rule.get('u_value')
    if not u:
        return None
    pct = round(u * 100)
    if pct < 5:
        return None
    # The action text often already states the loss, in sourced wording that is
    # better than ours. Saying it twice in one message reads as a machine.
    if '%' in action_text or 'टक्क' in action_text:
        return None
    return f"न केल्यास उत्पादनात अंदाजे {pct}% घट येऊ शकते."


def _when_sentence(rule, ctx) -> str | None:
    dap = ctx.get('dap')
    dtp = ctx.get('days_to_planting')
    dth = ctx.get('days_to_harvest')
    stage = rule.get('stage')

    if dap is not None and dap >= 0:
        if rule.get('delivery') == 'WINDOW':
            return f"आज पिकाला {dap} दिवस झाले आहेत."
        return f"पिकाला {dap} दिवस झाले आहेत."
    if dtp:
        return f"लागवडीला {dtp} दिवस उरले आहेत."
    if dth is not None and dth <= 60:
        return f"काढणीला सुमारे {dth} दिवस उरले आहेत."
    if stage:
        return None
    return None


def _confidence_note(rule) -> str | None:
    c = rule['reasoning']['confidence_score']
    sc = rule.get('source_class')
    if sc in ('EST', 'FIELD') or c < 0.72:
        return "हा सल्ला अंदाजावर आधारित आहे; प्रत्यक्ष मोजमापाने तो अधिक अचूक होईल."
    return None


def reads_as_engine_instruction(text: str) -> bool:
    """True where the message still addresses the engine rather than the farmer."""
    return bool(ENGINE_VERB.search(text))


@dataclass
class Message:
    rule_id: str
    severity: str
    priority_score: float
    what_mr: str
    when_mr: str | None
    why_mr: str | None
    if_not_mr: str | None
    note_mr: str | None
    override_note: str | None
    bundled_with: list = field(default_factory=list)
    engine_speak: bool = False

    def render(self, width=76) -> str:
        icon = SEV_ICON[self.severity]
        head = f"{icon} {SEV_LABEL_MR[self.severity]}"
        lines = [head, "   " + self.what_mr]
        for extra in (self.when_mr, self.why_mr, self.if_not_mr):
            if extra:
                lines.append("   " + extra)
        if self.bundled_with:
            lines.append("   सोबतच: " + ", ".join(self.bundled_with))
        if self.note_mr:
            lines.append("   " + self.note_mr)
        if self.override_note:
            lines.append("   " + self.override_note)
        return "\n".join(lines)


def compose(rule, ctx, bundled_titles=None, override_note=None, severity=None) -> Message:
    u = rule.get('u_value') or 0
    score = round(u * (2.0 if rule['recoverability'] == 'none' else 1.0), 4)

    full = rule['action']['marathi'].strip()
    # Some actions are written as instructions to the engine ("issue an alert",
    # "flag this"). The farmer needs the consequence, not the mechanism.
    for engine_phrase, farmer_phrase in ENGINE_TO_FARMER:
        full = full.replace(engine_phrase, farmer_phrase)
    full = ENGINE_TAIL.sub(' ', full).strip()
    parts = [p for p in re.split(r'(?<=[.।])\s+', full) if p.strip()]
    # A first sentence that is only a label carries no instruction. Fold the
    # next sentence in until there is something the farmer can act on.
    what_short, i = (parts[0].strip() if parts else full), 1
    while i < len(parts) and len(re.sub(r'[.।\s]', '', what_short)) < 18:
        what_short = (what_short + ' ' + parts[i].strip()).strip()
        i += 1
    why = ' '.join(parts[i:]).strip() or None

    return Message(
        rule_id=rule['rule_id'],
        severity=severity or rule['severity'],
        priority_score=score,
        what_mr=what_short,
        when_mr=_when_sentence(rule, ctx),
        why_mr=why,
        if_not_mr=_loss_sentence(rule, full),
        note_mr=_confidence_note(rule),
        override_note=override_note,
        bundled_with=bundled_titles or [],
        engine_speak=reads_as_engine_instruction(what_short),
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class Runner:
    def __init__(self):
        known, rules = set(), {}
        for fn in FILES:
            d = json.loads(Path(fn).read_text(encoding='utf-8'))
            sch = d['_schema']
            known |= set(sch.get('farm_brain_fields', {}))
            known |= set(sch.get('additions', {}).get('new_farm_brain_fields', {}))
            for r in d['rules']:
                rules[r['rule_id']] = r
        self.rules = rules
        self.allowed = known | SYNTHETIC | {f + '__duration' for f in known}
        self.compiled = {rid: parse(spec['expr'], self.allowed)
                         for rid, spec in TRIGGERS.items() if rid in rules}
        self.prec = Precedence()
        self.notifier = Notifier()
        self.overrides = OverrideStore(rules)

    def run(self, ctx: dict, day: date, *, plot_id=None, cluster_id=None,
            answered: set | None = None, attempted: set | None = None) -> dict:
        answered = answered or set()
        attempted = attempted or set()

        fired, unknown, cleared = [], [], []
        applied_overrides = {}

        for rid, node in self.compiled.items():
            eff = self.overrides.effective(rid, day, plot_id, cluster_id)
            if eff['disabled']:
                continue
            # an override may have rewritten the expression
            n = node
            if eff['expr'] and eff['expr'] != self.rules[rid]['trigger'].get('expr'):
                try:
                    n = parse(eff['expr'], self.allowed)
                except Exception:
                    n = node
            r = evaluate(n, ctx)
            if r.outcome == TV.TRUE:
                sev = eff['severity'] or self.rules[rid]['severity']
                fired.append(Fired(rid, sev, self.rules[rid]['priority'],
                                   self.rules[rid].get('u_value')))
                if eff['overrides']:
                    applied_overrides[rid] = eff['overrides']
            else:
                cleared.append(rid)
                if r.outcome == TV.UNKNOWN:
                    unknown.append((rid, r.missing, r.why('mr')))

        for rid in cleared:
            self.notifier.clear(rid, day)

        dec = self.prec.resolve(fired, answered)

        delivered, held = [], []
        for rid in dec.issued:
            eff_delivery = None
            ov = self.overrides.effective(rid, day, plot_id, cluster_id)
            if ov['delivery']:
                eff_delivery = ov['delivery']
            if eff_delivery:
                self.notifier.delivery[rid] = eff_delivery
            iss = self.notifier.decide(rid, day, action_attempted=(rid in attempted))
            (delivered if iss else held).append(rid)

        eff_sev = {f.rule_id: f.severity for f in fired}   # precedence may have raised it

        messages = []
        for rid in delivered:
            rule = self.rules[rid]
            titles = []
            for b in dec.bundles.get(rid, []):
                t = re.split(r'[—.।]', self.rules[b]['action']['marathi'])[0].strip()
                titles.append(t)
            note = None
            if rid in applied_overrides:
                o = applied_overrides[rid][0]
                note = f"({o['by']} यांनी या शेतासाठी बदल केला आहे — {o['rationale'][:52]}…)"
            messages.append(compose(rule, ctx, titles, note, eff_sev.get(rid)))

        messages.sort(key=lambda m: (SEV_RANK[m.severity], -m.priority_score))

        # diagnosis, only when there is something to diagnose
        dxr = None
        obs = {k: ctx.get(k) for k in
               ['central_shoot_dead','rhizome_smell','rhizome_texture','ooze_test_result',
                'wilt_while_green','stem_ooze_type','leaf_yellowing_pattern',
                'soil_free_lime_present','air_temp_above_35_3d','soil_moisture_saturated']
               if ctx.get(k) is not None}
        if obs:
            dxr = diagnose(obs)

        return dict(day=day, messages=messages, diagnosis=dxr,
                    fired=[f.rule_id for f in fired], held=held,
                    suppressed=[(a, b) for a, b, _ in dec.suppressed],
                    superseded=[(a, b) for a, b, _ in dec.superseded],
                    escalated=dec.escalated, unknown=unknown,
                    fallback=dec.fallback_used)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_day(res, ctx, show_internals=False) -> str:
    out = []
    dap = ctx.get('dap')
    stage = ctx.get('current_stage')
    head = f"  {res['day']}"
    if dap is not None:
        head += f"   ·   पिकाला {dap} दिवस   ·   अवस्था {stage}"
    elif ctx.get('days_to_planting'):
        head += f"   ·   लागवडीला {ctx['days_to_planting']} दिवस"
    out.append("─" * 72)
    out.append(head)
    out.append("─" * 72)

    if not res['messages'] and not res['diagnosis']:
        out.append("\n  आज कोणतीही कृती आवश्यक नाही.\n")
    else:
        for m in res['messages']:
            out.append("")
            out.append(m.render())
        out.append("")

    if res['diagnosis'] and res['diagnosis']['state'] != 'NO_CANDIDATE':
        d = res['diagnosis']
        out.append(f"  🔍 निदान  [{d['state']}]")
        out.append(f"     {d['message_mr']}")
        for c in d['candidates'][:3]:
            out.append(f"       {c.confidence:.2f}  {c.name_mr}")
        out.append("")

    if show_internals:
        out.append("  ── अंतर्गत ──")
        out.append(f"     फिरले {len(res['fired'])} · दिले {len(res['messages'])} · "
                   f"policy ने रोखले {len(res['held'])} · "
                   f"दडपले {len(res['suppressed']) + len(res['superseded'])}")
        if res['suppressed']:
            out.append("     दडपले: " + ", ".join(f"{a}←{b}" for a, b in res['suppressed'][:4]))
        if res['unknown']:
            out.append(f"     माहिती अपुरी ({len(res['unknown'])}):")
            for rid, missing, why in res['unknown'][:3]:
                out.append(f"       {rid}: {', '.join(missing) if missing else why}")
    return "\n".join(out)


# ---------------------------------------------------------------------------

def demo_context(kind='earthing_day'):
    """Realistic Farm Brain snapshots for inspection."""
    base = dict(
        soil_type='vertisol', soil_texture_class='heavy', soil_depth_cm=45,
        percolation_time_hours=9, drainage_outlet_present=True,
        variety='mahima', has_drip=True, planting_layout='broad_ridge',
        area_acre=1.0, ceiling_quintal_per_acre=113,
        ceiling_basis='variety_plus_broad_ridge_113', yield_target_quintal_per_acre=90,
        seasonal_water_requirement_litres=2_700_000,
        water_available_oct_feb_litres=2_900_000,
        season_water_plan_basis='poor_year',
        drainage_levels_present=3, main_drain_connected=True,
        moisture_probe_depth_cm=12, soil_test_available=True, calibration_done=True,
        vwc_saturation=45.0, vwc_field_capacity=38.0, vwc_stress_threshold=22.0,
        consent_advisory=True, consent_research=True, cluster_anonymised=True,
        seed_retained_or_purchased='purchased', field_history_rot=False,
        field_history_wilt=False, intercrop_selected='marigold',
        pre_sanction_received=True, subsidy_scheme_applied='drip',
        breakeven_price_per_quintal=1450, plants_per_acre=24300,
        seed_piece_weight_g=35, cost_seed=40000, drying_method='simple_sun',
        ppe_available=True, processing_trained_operator=True,
        seed_supplier_identified=True, deep_ploughing_done=True, kulav_passes=4,
        solarization_done=True, mulch_stage_1_done=True, emergence_started=True,
        establishment_pct=88.0, castor_bait_prepared_date='done',
        light_trap_installed=True, micronutrient_spray_1_done=True,
        pest_scouting_date='done', pmfby_notified_for_ginger='no',
    )

    if kind == 'earthing_day':
        base.update(dap=82, current_stage='G3', current_month=8,
                    air_temp_max_c=30.5, rainfall_mm=2.0, rh_pct=78.0,
                    soil_moisture_vwc=34.0, soil_moisture_vwc__duration=0,
                    rh_pct__duration=24, forecast_rain_48h_mm=3.0,
                    rain_gap_days=1, dry_spell_days=1, days_to_harvest=153,
                    flowering_observed=False, tillers_per_plant=12.0,
                    labour_arranged_date='set', planting_date='2026-06-05')

    elif kind == 'saturation':
        base.update(dap=95, current_stage='G3', current_month=9,
                    air_temp_max_c=29.0, rainfall_mm=48.0, rh_pct=93.0,
                    soil_moisture_vwc=48.0, soil_moisture_vwc__duration=30,
                    rh_pct__duration=96, forecast_rain_48h_mm=35.0,
                    rain_gap_days=0, dry_spell_days=0, days_to_harvest=140,
                    earthing_up_date='done', n_split_2_date='done',
                    mulch_stage_2_done=True, water_stress_after_earthing_done=True,
                    micronutrient_spray_2_done=True, flowering_observed=False,
                    tillers_per_plant=12.0, central_shoot_dead=True,
                    rhizome_smell='sour_foul', rhizome_texture='mushy_wet',
                    planting_date='2026-06-05')

    elif kind == 'heat_spray':
        base.update(dap=50, current_stage='G2', current_month=7,
                    air_temp_max_c=39.5, rainfall_mm=0.0, rh_pct=52.0,
                    soil_moisture_vwc=30.0, soil_moisture_vwc__duration=0,
                    rh_pct__duration=0, forecast_rain_48h_mm=0.0,
                    rain_gap_days=9, dry_spell_days=9, days_to_harvest=185,
                    micronutrient_spray_1_done=False, flowering_observed=False,
                    planting_date='2026-06-05')

    elif kind == 'preseason':
        base.update(dap=None, days_to_planting=90, current_month=3,
                    air_temp_max_c=36.0, rainfall_mm=0.0, rh_pct=34.0,
                    deep_ploughing_done=False, solarization_done=False,
                    mulch_stage_1_done=False, emergence_started=False,
                    establishment_pct=None, castor_bait_prepared_date=None,
                    light_trap_installed=False, micronutrient_spray_1_done=False,
                    seed_supplier_identified=False, pest_scouting_date=None,
                    pmfby_notified_for_ginger='unverified',
                    current_stage='G0', vafsa_state='workable', kulav_passes=0)

    elif kind == 'quiet':
        base.update(dap=175, current_stage='G4', current_month=11,
                    air_temp_max_c=29.0, rainfall_mm=0.0, rh_pct=48.0,
                    soil_moisture_vwc=33.0, soil_moisture_vwc__duration=0,
                    rh_pct__duration=0, forecast_rain_48h_mm=0.0,
                    rain_gap_days=4, dry_spell_days=4, days_to_harvest=60,
                    earthing_up_date='done', earthing_up_2_date='done',
                    n_split_2_date='done', k_late_split_1_date='done',
                    k_late_split_2_date='done', mulch_stage_2_done=True,
                    mulch_stage_3_done=True, micronutrient_spray_2_done=True,
                    water_stress_after_earthing_done=True, flowering_observed=True,
                    sample_dig_120_done=True, planting_date='2026-06-05')
    return base


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', default='all')
    ap.add_argument('--internals', action='store_true')
    a = ap.parse_args()

    cases = (['preseason', 'earthing_day', 'heat_spray', 'saturation', 'quiet']
             if a.case == 'all' else [a.case])
    LABEL = {'preseason':'हंगामापूर्व — नांगरट बाकी',
             'earthing_day':'उटाळणीचा दिवस (८२ DAP)',
             'heat_spray':'फवारणीची वेळ, पण ३९.५ अंश',
             'saturation':'सप्टेंबर — पाणी साचले, सुरळी मेली',
             'quiet':'सर्व कामे झाली, शांत दिवस'}

    for c in cases:
        r = Runner()
        ctx = demo_context(c)
        day = date(2026, 8, 26)
        res = r.run(ctx, day)
        print(f"\n\n╔{'═'*70}╗")
        print(f"  {LABEL[c]}")
        print(f"╚{'═'*70}╝")
        print(render_day(res, ctx, show_internals=a.internals))
