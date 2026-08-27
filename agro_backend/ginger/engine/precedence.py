#!/usr/bin/env python3
"""
AgroGuardian AI — Precedence & Multi-Diagnosis Resolver
=======================================================

Two problems, one module, because they are the same problem seen twice:
several rules fire at once and the engine has to decide what the farmer sees.

PART 1 — PRECEDENCE

Severity alone gives the wrong answer. A worked case from the knowledge base:

    D04-MC-001  yellow  "spray micronutrients"      (dap 45-60)
    D04-MC-004  info    "above 35 C, postpone"      (heat / rain forecast)

Ranking by severity lets the spray win and the leaves scorch. D04-MC-004 is
not a competing instruction — it is a CONDITION ON another instruction.

So relations are typed, not ranked:

    SUPPRESSES   B stops A from being issued at all
    SUPERSEDES   B replaces A; only B is shown
    ESCALATES    B raises A's severity; one message, higher urgency
    BUNDLES      A and B travel together in one field visit
    SEQUENCES    A must be answered before B is evaluated

Where no typed relation exists, the fallback ordering is
severity, then priority, then u_value — and the engine records that a
fallback was used, because an unrecorded fallback is how the spray case
would slip back in.

PART 2 — MULTI-DIAGNOSIS

The Domain 6 differential returns one answer. Reality does not.
Rot and heat scorch can both be present; nitrogen deficiency and iron
lock-up can coexist on calcareous soil.

So diagnosis returns a RANKED SET with confidence, and the engine
distinguishes three states:

    CONFIRMED    one cause, a decisive marker present
    PROBABLE     one cause clearly ahead, others not excluded
    AMBIGUOUS    two or more within the confidence band -> ask, do not treat

Domain 12 D12-CLS-001 requires diagnosis before treatment. AMBIGUOUS is
where that rule earns its place: the engine says which test separates the
candidates rather than guessing.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

SEV_RANK = {'blocking': 0, 'red': 1, 'yellow': 2, 'info': 3}


# ---------------------------------------------------------------------------
# PART 1 — Precedence
# ---------------------------------------------------------------------------

RELATIONS = ('SUPPRESSES', 'SUPERSEDES', 'ESCALATES', 'BUNDLES', 'SEQUENCES')


@dataclass(frozen=True)
class Relation:
    subject: str          # the rule that acts
    relation: str
    object: str           # the rule acted upon
    reason_en: str
    reason_mr: str


# The typed relations. Every one traces to a rule pair that can genuinely
# fire together, not to a hypothetical.
PRECEDENCE = [

 # --- suppression: a condition that must stop an instruction -------------
 Relation('D04-MC-004', 'SUPPRESSES', 'D04-MC-001',
   'Leaves scorch above 35 C and rain washes foliar application off. The spray '
   'instruction must not be issued while either holds.',
   'पानं ३५ अंशांवर करपतात आणि पाऊस फवारणी धुऊन नेतो. या दोन्हीपैकी काहीही असेल तर फवारणीची सूचना देऊ नये.'),

 Relation('D04-MC-004', 'SUPPRESSES', 'D04-MC-002',
   'Same condition applies to the second micronutrient spray.',
   'दुसऱ्या सूक्ष्म अन्नद्रव्य फवारणीलाही हीच अट लागू.'),

 Relation('D07-HS-004', 'SUPPRESSES', 'D05-CH-006',
   'Any foliar spray is suppressed above 35 C or before rain.',
   'तापमान ३५ अंशांवर असल्यास किंवा पावसापूर्वी कोणतीही फवारणी दडपली जाते.'),

 Relation('D03-MN-002', 'SUPPRESSES', 'D03-WR-001',
   'Saturation measured by the probe overrides the water balance computation. '
   'The sensor measures; the table estimates.',
   'probe ने मोजलेली संपृक्तता पाण्याच्या गणिताला ओलांडते. sensor मोजतो, तक्ता अंदाज लावतो.'),

 Relation('D03-MN-002', 'SUPPRESSES', 'D03-WR-002',
   'Saturation override applies to the formula route as well as the table.',
   'संपृक्ततेचा override सूत्रावरही लागू, फक्त तक्त्यावर नाही.'),

 Relation('D03-WL-001', 'SUPPRESSES', 'D03-MN-003',
   'A field standing in water does not need the dry-spell irrigation rule.',
   'पाणी साचलेल्या शेताला पावसाच्या खंडाचा सिंचन नियम लागू होत नाही.'),

 Relation('D08-EU-002', 'SUPPRESSES', 'D08-EU-001',
   'Once the flowering spike opens the earthing-up window has closed. Doing it '
   'late damages roots during bulking without the compensating regrowth.',
   'हुरडे बांड आल्यावर उटाळणीची मुदत संपते. उशिरा केल्यास गड्डा भरत असताना मुळे तुटतात आणि नवी मुळे येण्यास वेळ नसतो.'),

 Relation('D04-DG-003', 'SUPPRESSES', 'D04-NS-001',
   'Soft rot or wilt present. Fertiliser applied now is money spent while the '
   'crop is being lost.',
   'कूज किंवा मर रोग आहे. आता खत देणे म्हणजे पीक जात असताना पैसा खर्च करणे.'),

 Relation('D04-DG-003', 'SUPPRESSES', 'D04-PK-001',
   'Same handover: nutrient advisory stops when disease is confirmed.',
   'रोग निश्चित झाल्यावर खताचा सल्ला थांबतो.'),

 Relation('D05-NE-001', 'SUPPRESSES', 'D08-GR-002',
   'Low tiller count is the earliest nematode sign. Spraying a hormone to raise '
   'tillers would mask the pest rather than treat it.',
   'फुटवे कमी असणे हे सूत्रकृमींचे पहिले लक्षण आहे. फुटवे वाढवण्यासाठी संप्रेरक फवारल्यास किडीवर पडदा पडतो.'),

 Relation('D06-CH-001', 'SUPPRESSES', 'D06-DX-003',
   'Bacterial wilt confirmed. No fungicide has activity against a bacterium, '
   'so the soft rot treatment path must not be offered.',
   'मर रोग निश्चित. जिवाणूवर कोणतेही बुरशीनाशक चालत नाही, म्हणून कंदकुजीचा उपचार मार्ग दाखवू नये.'),

 Relation('D09-SF-002', 'SUPPRESSES', 'D09-MT-001',
   'Pre-harvest interval not satisfied. Maturity advice must not lead to a '
   'harvest that carries residue.',
   'प्रतीक्षा कालावधी पूर्ण नाही. पक्वतेचा सल्ला अवशेषयुक्त काढणीकडे नेऊ नये.'),

 Relation('D02-DR-001', 'SUPPRESSES', 'D08-LY-001',
   'If the plot is being advised against ginger, layout advice is premature.',
   'या शेतात अद्रक टाळण्याचा सल्ला असेल तर लागवड पद्धतीचा सल्ला अकाली आहे.'),

 Relation('D01-HV-002', 'SUPPRESSES', 'D01-HV-003',
   'Maturity conclusion blocked before 200 DAP, so harvest scheduling must not '
   'proceed on a yellowing signal alone.',
   'दोनशे दिवसांआधी पक्वतेचा निष्कर्ष अडवला जातो, म्हणून फक्त पिवळेपणावरून काढणीचे नियोजन करू नये.'),

 Relation('D01-HV-004', 'SUPPRESSES', 'D09-MT-004',
   'Seed crop must reach full maturity. The 75 percent market flexibility does '
   'not apply to the fraction kept for seed.',
   'बेण्यासाठीचे पीक पूर्ण पक्व झालेच पाहिजे. ७५ टक्के पक्वतेची बाजारातील सवलत बेण्याला लागू नाही.'),

 Relation('D09-MT-003', 'SUPPRESSES', 'D09-MT-004',
   'Same constraint stated in the harvest domain.',
   'हीच अट काढणी Domain मध्येही.'),

 Relation('D04-SB-001', 'SUPPRESSES', 'D04-NP-001',
   'Doses must not be set from the probe. Where no soil test exists the safe '
   'default range is used and marked medium confidence, not a probe-derived figure.',
   'probe वरून मात्रा ठरवू नये. माती परीक्षण नसल्यास सुरक्षित श्रेणी मध्यम विश्वासार्हतेसह वापरावी, probe चा आकडा नाही.'),

 # --- supersession: a more specific rule replaces a general one -----------
 Relation('D03-MN-004', 'SUPERSEDES', 'D03-MN-003',
   'In G3 and G4 the intervention point is 7 days, not the general 10 to 12. '
   'Showing both would be contradictory.',
   'G3 आणि G4 मध्ये हस्तक्षेपाची मर्यादा ७ दिवस आहे, सामान्य १० ते १२ नाही. दोन्ही दाखवणे परस्परविरोधी होईल.'),

 Relation('D09-MT-002', 'SUPERSEDES', 'D09-MT-001',
   'Before 200 DAP, yellowing has at least six causes. The maturity reading is '
   'blocked until the diagnosis clears it.',
   'दोनशे दिवसांआधी पिवळेपणाची किमान सहा कारणे आहेत. निदान होईपर्यंत पक्वतेचा निष्कर्ष अडवला जातो.'),

 Relation('D07-CY-001', 'SUPERSEDES', 'D03-WL-003',
   'Same event, one alert. Duplication group post_monsoon_cyclone_saturation.',
   'एकच घटना, एकच इशारा.'),

 Relation('D06-MU-001', 'SUPERSEDES', 'D03-MU-001',
   'One mulch programme, three domains. Duplication group '
   'three_stage_mulch_programme; the disease value is the full programme value.',
   'एकच आच्छादन कार्यक्रम, तीन Domain. रोग-मूल्य हे संपूर्ण कार्यक्रमाचे मूल्य आहे.'),

 Relation('D06-CH-003', 'SUPERSEDES', 'D05-CH-003',
   'One pre-harvest interval block, not three. Duplication group '
   'pre_harvest_interval_block.',
   'एकच प्रतीक्षा-कालावधी अडथळा, तीन नाही.'),

 Relation('D08-TL-002', 'SUPERSEDES', 'D02-TL-003',
   'One vafsa notification. Duplication group vafsa_workable_window.',
   'वाफशाची एकच सूचना.'),

 Relation('D01-TM-001', 'SUPERSEDES', 'D07-HS-001',
   'One heat instruction, not three. The lifecycle rule carries the stage context '
   'and the same expert-amended 35 C threshold.',
   'उष्णतेची एकच सूचना, तीन नाहीत. Domain 1 चा नियम अवस्थेचा संदर्भ देतो आणि तीच ३५ अंशांची सुधारित मर्यादा वापरतो.'),

 Relation('D01-TM-001', 'SUPERSEDES', 'D07-TM-001',
   'Same condition, same advice, different domain.',
   'तीच अट, तोच सल्ला, वेगळा Domain.'),

 Relation('D03-DS-001', 'BUNDLES', 'D03-DS-002',
   'Lateral spacing and system flow are one drip design conversation.',
   'नळीतील अंतर आणि प्रवाह — ठिबकाच्या मांडणीचा एकच निर्णय.'),

 Relation('D07-HS-003', 'SUPPRESSES', 'D07-HS-002',
   'Heat plus dryness together is the more specific case.',
   'उष्णता आणि कोरडेपणा एकत्र असणे ही अधिक नेमकी स्थिती आहे.'),

 Relation('D03-WL-001', 'SUPPRESSES', 'D03-WL-004',
   'A saturation alert already covers the G1 case; two messages for one field '
   'of standing water is noise.',
   'साचलेल्या पाण्याचा इशारा आधीच दिला आहे. एकाच स्थितीसाठी दोन संदेश म्हणजे गोंगाट.'),

 # --- escalation: raise urgency, do not add a message --------------------
 Relation('D03-WL-002', 'ESCALATES', 'D03-WL-001',
   'Saturation at G2 or G3 is the peak soft rot window. Same alert, higher '
   'severity, not a second notification.',
   'G2 किंवा G3 मध्ये पाणी साचणे ही कंदकुजीची शिखर वेळ. तोच इशारा, जास्त तीव्रतेने — दुसरी सूचना नाही.'),

 Relation('D06-SR-001', 'ESCALATES', 'D03-WL-001',
   'The saturation alert and the preventive rot protocol are one event seen '
   'from water and from disease.',
   'संपृक्ततेचा इशारा आणि कंदकूज प्रतिबंधक कृती ही एकच घटना — पाणी आणि रोग या दोन बाजूंनी.'),

 Relation('D06-BW-002', 'ESCALATES', 'D05-NE-001',
   'Nematodes raise bacterial wilt risk as well as the direct nematode loss.',
   'सूत्रकृमी थेट नुकसानासोबत मर रोगाचीही जोखीम वाढवतात.'),

 # --- bundling: one field visit ------------------------------------------
 Relation('D08-EU-001', 'BUNDLES', 'D04-NS-002',
   'Earthing up and the final nitrogen split are the same visit.',
   'उटाळणी आणि नत्राचा शेवटचा हप्ता एकाच फेरीत.'),
 Relation('D08-EU-001', 'BUNDLES', 'D08-MU-002',
   'Mulch stage two goes with earthing up.',
   'आच्छादनाचा दुसरा टप्पा उटाळणीसोबत.'),
 Relation('D08-EU-001', 'BUNDLES', 'D08-EU-005',
   'Covering exposed rhizomes happens during earthing up.',
   'उघडे गड्डे झाकणे उटाळणीच्या वेळीच.'),
 Relation('D08-EU-004', 'BUNDLES', 'D04-PK-001',
   'Second earthing carries the potassium split.',
   'दुसऱ्या उटाळणीसोबत पालाशाचा हप्ता.'),

 # --- sequencing: answer this before evaluating that ---------------------
 Relation('D06-DX-001', 'SEQUENCES', 'D06-DX-003',
   'Diagnosis precedes treatment without exception.',
   'निदान झाल्याशिवाय उपचार नाही — अपवाद नाही.'),
 Relation('D06-DX-001', 'SEQUENCES', 'D06-CH-002',
   'No chemical option is surfaced before the differential is resolved.',
   'निदान होईपर्यंत रासायनिक पर्याय दाखवला जात नाही.'),
 Relation('D04-DG-001', 'SEQUENCES', 'D04-NS-001',
   'Yellowing is diagnosed before nitrogen is recommended.',
   'पिवळेपणाचे निदान झाल्यावरच नत्र सुचवावा.'),
 Relation('D02-ST-002', 'SEQUENCES', 'D02-DR-001',
   'The percolation test must be run before the drainage verdict is issued.',
   'निचऱ्याचा निर्णय देण्यापूर्वी खड्डा चाचणी झाली पाहिजे.'),
]


@dataclass
class Fired:
    rule_id: str
    severity: str
    priority: int
    u_value: float | None = None
    payload: dict = field(default_factory=dict)


@dataclass
class Decision:
    issued: list          # rule_ids the farmer sees
    suppressed: list      # (rule_id, by, reason_mr)
    superseded: list
    escalated: list       # (rule_id, by)
    bundles: dict         # anchor -> [rule_ids]
    sequence_waits: list  # (rule_id, waits_for)
    fallback_used: list   # pairs resolved by severity order, no typed relation
    trace: list


class Precedence:
    def __init__(self, relations=PRECEDENCE):
        self.by_obj = defaultdict(list)
        self.by_sub = defaultdict(list)
        for r in relations:
            self.by_obj[r.object].append(r)
            self.by_sub[r.subject].append(r)

    def resolve(self, fired: list[Fired], answered: set[str] | None = None) -> Decision:
        answered = answered or set()
        ids = {f.rule_id for f in fired}
        by_id = {f.rule_id: f for f in fired}

        suppressed, superseded, escalated, waits, trace = [], [], [], [], []
        removed = set()

        for f in fired:
            for rel in self.by_obj.get(f.rule_id, []):
                if rel.subject not in ids:
                    continue
                if rel.relation == 'SUPPRESSES':
                    removed.add(f.rule_id)
                    suppressed.append((f.rule_id, rel.subject, rel.reason_mr))
                    trace.append(f"{rel.subject} SUPPRESSES {f.rule_id}")
                elif rel.relation == 'SUPERSEDES':
                    removed.add(f.rule_id)
                    superseded.append((f.rule_id, rel.subject, rel.reason_mr))
                    trace.append(f"{rel.subject} SUPERSEDES {f.rule_id}")
                elif rel.relation == 'ESCALATES':
                    escalated.append((f.rule_id, rel.subject))
                    removed.add(rel.subject)          # merge into the escalated one
                    cur = SEV_RANK[by_id[f.rule_id].severity]
                    new = SEV_RANK[by_id[rel.subject].severity]
                    if new < cur:
                        by_id[f.rule_id].severity = by_id[rel.subject].severity
                    trace.append(f"{rel.subject} ESCALATES {f.rule_id}")
                elif rel.relation == 'SEQUENCES':
                    if rel.subject not in answered:
                        removed.add(f.rule_id)
                        waits.append((f.rule_id, rel.subject))
                        trace.append(f"{f.rule_id} waits for {rel.subject}")

        surviving = [by_id[i] for i in ids if i not in removed]

        # bundling
        bundles = defaultdict(list)
        bundled_members = set()
        for f in surviving:
            for rel in self.by_sub.get(f.rule_id, []):
                if rel.relation == 'BUNDLES' and rel.object in {s.rule_id for s in surviving}:
                    bundles[f.rule_id].append(rel.object)
                    bundled_members.add(rel.object)

        # fallback ordering, and record that it was used
        fallback = []
        anchors = [f for f in surviving if f.rule_id not in bundled_members]
        anchors.sort(key=lambda f: (SEV_RANK[f.severity], -f.priority, -(f.u_value or 0)))
        for i in range(len(anchors) - 1):
            a, b = anchors[i], anchors[i + 1]
            typed = any(r.object == b.rule_id and r.subject == a.rule_id
                        for r in self.by_sub.get(a.rule_id, []))
            if not typed and a.severity != b.severity:
                fallback.append((a.rule_id, b.rule_id))

        return Decision(
            issued=[f.rule_id for f in anchors],
            suppressed=suppressed, superseded=superseded, escalated=escalated,
            bundles=dict(bundles), sequence_waits=waits,
            fallback_used=fallback, trace=trace)


# ---------------------------------------------------------------------------
# PART 2 — Multi-diagnosis
# ---------------------------------------------------------------------------

@dataclass
class Candidate:
    cause: str
    name_mr: str
    confidence: float
    evidence_for: list = field(default_factory=list)
    evidence_against: list = field(default_factory=list)
    decisive_marker: bool = False
    next_test_mr: str = ''
    treatment_rule: str = ''


# Domain 4 and Domain 6 differential, expressed as weighted evidence rather
# than a single-answer tree. Weights are author estimates and are marked so.
YELLOWING = {
 'soft_rot': dict(name_mr='कंदकूज', rule='D06-DX-003',
   decisive=[('central_shoot_dead', True)],
   supports=[('rhizome_smell','sour_foul',0.35),('rhizome_texture','mushy_wet',0.30),
             ('soil_moisture_saturated',True,0.15),('shoot_pulls_out_easily',True,0.15)],
   excludes=[('ooze_test_result','milky_thread')],
   next_test_mr='एक रोप उकरून गड्डा दाबून पहा — पचपचीत आणि आंबट वास?'),

 'bacterial_wilt': dict(name_mr='मर रोग', rule='D06-DX-002',
   decisive=[('ooze_test_result','milky_thread')],
   supports=[('wilt_while_green',True,0.40),('stem_ooze_type','milky_yellowish',0.35),
             ('stem_cut_colour','greyish_yellow',0.20),('field_history_wilt',True,0.10)],
   excludes=[],
   next_test_mr='खोड कापून स्वच्छ पाण्याच्या ग्लासात लटकवा — दुधाळ धागा उतरतो का?'),

 'fusarium': dict(name_mr='फ्युजेरियम', rule='D06-DX-004',
   decisive=[],
   supports=[('rhizome_texture','dry_rot',0.45),('stem_cut_colour','brown_vascular',0.30)],
   excludes=[('ooze_test_result','milky_thread')],
   next_test_mr='गड्डा कोरडा कुजला आहे की पचपचीत?'),

 'nitrogen_deficiency': dict(name_mr='नत्राची कमतरता', rule='D04-NS-001',
   decisive=[],
   supports=[('leaf_yellowing_pattern','uniform_old',0.55),('n_split_1_date',None,0.20)],
   excludes=[('leaf_yellowing_pattern','interveinal_new')],
   next_test_mr='जुनी पानं पिवळी की नवी?'),

 'iron_zinc_lockup': dict(name_mr='लोह/जस्त अनुपलब्धता', rule='D04-DG-002',
   decisive=[],
   supports=[('leaf_yellowing_pattern','interveinal_new',0.55),('soil_free_lime_present',True,0.30)],
   excludes=[('leaf_yellowing_pattern','uniform_old')],
   next_test_mr='शिरा हिरव्या आणि मधला भाग पिवळा — नव्या पानांवर?'),

 'waterlogging': dict(name_mr='पाणी साचणे', rule='D03-WL-001',
   decisive=[],
   supports=[('soil_moisture_saturated',True,0.50),('drainage_levels_present',None,0.20)],
   excludes=[],
   next_test_mr='मुळाजवळची माती ओली आहे का?'),

 'heat_stress': dict(name_mr='उष्णतेची इजा', rule='D07-HS-002',
   decisive=[],
   supports=[('air_temp_above_35_3d',True,0.45),('leaf_yellowing_pattern','margin_scorch',0.35),
             ('leaf_spot_rings_visible',False,0.20)],
   excludes=[],
   next_test_mr='पान सूर्याकडे धरा — ठिपक्यांत वर्तुळे दिसतात का?'),
}

AMBIGUITY_BAND = 0.15     # candidates within this of the leader are not excluded


def diagnose(observations: dict, model=YELLOWING) -> dict:
    cands = []
    for code, spec in model.items():
        # exclusion first
        excluded = any(observations.get(f) == v for f, v in spec['excludes'])
        if excluded:
            continue
        decisive = any(observations.get(f) == v for f, v in spec['decisive'])
        score, ev_for = (1.0, ['decisive marker']) if decisive else (0.0, [])
        if not decisive:
            for f, v, w in spec['supports']:
                got = observations.get(f)
                if got is None:
                    continue
                if (v is None and got is not None) or got == v:
                    score += w
                    ev_for.append(f"{f}={got!r}")
        if score > 0:
            cands.append(Candidate(code, spec['name_mr'], round(min(score, 1.0), 2),
                                   ev_for, [], decisive, spec['next_test_mr'], spec['rule']))

    cands.sort(key=lambda c: -c.confidence)
    if not cands:
        return dict(state='NO_CANDIDATE', candidates=[],
                    message_mr='पुरेशी माहिती नाही. खालील निरीक्षणे नोंदवा आणि पुन्हा तपासा.')

    top = cands[0]
    if top.decisive_marker:
        state = 'CONFIRMED'
    else:
        near = [c for c in cands[1:] if top.confidence - c.confidence <= AMBIGUITY_BAND]
        state = 'AMBIGUOUS' if near else 'PROBABLE'

    if state == 'CONFIRMED':
        msg = f"निदान निश्चित: {top.name_mr}."
    elif state == 'PROBABLE':
        msg = (f"बहुधा {top.name_mr} ({int(top.confidence*100)}%). "
               f"खात्रीसाठी: {top.next_test_mr}")
    else:
        names = ' किंवा '.join(c.name_mr for c in cands[:3])
        msg = (f"दोन शक्यता आहेत — {names}. उपचार करण्यापूर्वी वेगळे करा. "
               f"{top.next_test_mr}")

    return dict(state=state, candidates=cands,
                treatment_rule=top.treatment_rule if state == 'CONFIRMED' else None,
                message_mr=msg)


if __name__ == '__main__':
    print("═══ PART 1 — PRECEDENCE ═══\n")
    p = Precedence()

    print("प्रकरण: ४५ DAP, सूक्ष्म फवारणीची वेळ, पण तापमान ४० अंश")
    d = p.resolve([Fired('D04-MC-001','yellow',5,0.11), Fired('D04-MC-004','info',3)])
    print(f"  दाखवले   : {d.issued}")
    print(f"  दडपले    : {[(a,b) for a,b,_ in d.suppressed]}")
    print(f"  -> {d.suppressed[0][2] if d.suppressed else ''}\n")

    print("प्रकरण: ऑगस्ट, G3, १४ तास संपृक्तता")
    d = p.resolve([Fired('D03-WR-001','info',5), Fired('D03-MN-002','red',5),
                   Fired('D03-WL-001','red',5,0.35), Fired('D03-WL-002','red',5),
                   Fired('D06-SR-001','red',5,0.70)])
    print(f"  दाखवले   : {d.issued}")
    print(f"  दडपले    : {[(a,b) for a,b,_ in d.suppressed]}")
    print(f"  तीव्रता वाढवली: {d.escalated}\n")

    print("प्रकरण: ८२ DAP — Bundle 3")
    d = p.resolve([Fired('D08-EU-001','yellow',5,0.125), Fired('D04-NS-002','yellow',5),
                   Fired('D08-MU-002','yellow',4), Fired('D08-EU-005','yellow',5)])
    print(f"  दाखवले   : {d.issued}")
    print(f"  गुच्छ     : {d.bundles}\n")

    print("प्रकरण: पिवळेपणा, निदान झालेले नाही")
    d = p.resolve([Fired('D04-DG-001','red',5), Fired('D04-NS-001','yellow',4,0.10)])
    print(f"  दाखवले   : {d.issued}")
    print(f"  प्रतीक्षेत : {d.sequence_waits}\n")

    print("═══ PART 2 — MULTI-DIAGNOSIS ═══\n")
    cases = [
      ("दुधाळ धागा दिसला", {'ooze_test_result':'milky_thread','wilt_while_green':True}),
      ("सुरळी मेली, आंबट वास", {'central_shoot_dead':True,'rhizome_smell':'sour_foul'}),
      ("कडा करपल्या, ४० अंश, माती ओली",
        {'leaf_yellowing_pattern':'margin_scorch','air_temp_above_35_3d':True,
         'soil_moisture_saturated':True}),
      ("फक्त नवी पानं पिवळी, चुनखडी आहे",
        {'leaf_yellowing_pattern':'interveinal_new','soil_free_lime_present':True}),
      ("काहीच नोंदवलेले नाही", {}),
    ]
    for label, obs in cases:
        r = diagnose(obs)
        print(f"  {label}")
        print(f"    स्थिती: {r['state']}")
        for c in r['candidates'][:3]:
            print(f"      {c.confidence:.2f}  {c.name_mr:22s} {', '.join(c.evidence_for)}")
        print(f"    -> {r['message_mr']}\n")
