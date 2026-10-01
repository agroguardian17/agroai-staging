#!/usr/bin/env python3
"""
AgroGuardian AI — Regression Gate
=================================

One command that must pass before the knowledge base is regenerated or
deployed. It runs everything and adds the season-level assertions that
unit tests cannot express.

The season assertions exist because the two worst failures found so far were
both invisible to unit tests:

  - 998 messages across 301 days, one blocking rule repeating 301 times
  - a 39-day silence through G4, the stage where yield is actually made

Neither was a wrong rule. Both were the system behaving correctly at the
rule level and badly at the season level.
"""

import subprocess, sys, json
from pathlib import Path
from collections import Counter

# season-level bounds. Deliberately wide: these catch collapse, not drift.
BOUNDS = dict(
    max_messages=200,          # notification fatigue
    min_messages=40,           # engine gone quiet
    max_per_day=6,             # flooding on a single day
    max_silence_critical=21,   # days without advice in G1 / G3 / G4
    max_repeat_share=0.25,     # no single rule above this share of all messages
)

CRITICAL_STAGES = ('G1', 'G3', 'G4')


def run(cmd, label):
    r = subprocess.run([sys.executable, cmd], capture_output=True, text=True)
    ok = r.returncode == 0
    print(f"  {'✅' if ok else '❌'} {label}")
    if not ok:
        print(r.stdout[-2500:]); print(r.stderr[-1200:])
    return ok


def season_assertions():
    from simulate_season import run as run_season, SCENARIOS
    all_ok = True
    print()
    for name in SCENARIOS:
        res = run_season(name, seed=7, compliance=0.85)
        per_day = res['per_day']
        msgs = sum(n for _, _, _, n, _ in per_day)
        peak = max((n for _, _, _, n, _ in per_day), default=0)

        problems = []
        if msgs > BOUNDS['max_messages']:
            problems.append(f"{msgs} संदेश > {BOUNDS['max_messages']} — notification fatigue")
        if msgs < BOUNDS['min_messages']:
            problems.append(f"{msgs} संदेश < {BOUNDS['min_messages']} — engine गप्प")
        if peak > BOUNDS['max_per_day']:
            problems.append(f"एका दिवशी {peak} संदेश > {BOUNDS['max_per_day']}")

        for stg in CRITICAL_STAGES:
            ds = [n for _, _, st, n, _ in per_day if st == stg]
            gap = cur = 0
            for n in ds:
                cur = 0 if n else cur + 1
                gap = max(gap, cur)
            if gap > BOUNDS['max_silence_critical']:
                problems.append(f"{stg}: {gap} दिवस शांतता > {BOUNDS['max_silence_critical']}")

        if msgs:
            top_rule, top_n = res['issued'].most_common(1)[0]
            share = top_n / msgs
            if share > BOUNDS['max_repeat_share']:
                problems.append(f"{top_rule} = {round(share*100)}% संदेश > "
                                f"{round(BOUNDS['max_repeat_share']*100)}%")

        # a diagnosis event must never be reported more than a handful of times
        dx = Counter(x[3] for x in res['dx'])
        for cause, n in dx.items():
            if n > 5:
                problems.append(f"{cause} {n} वेळा निदान — edge detection तुटले")

        label = SCENARIOS[name]['label']
        if problems:
            all_ok = False
            print(f"  ❌ {label}")
            for p in problems: print(f"       {p}")
        else:
            gaps = []
            for stg in CRITICAL_STAGES:
                ds = [n for _, _, st, n, _ in per_day if st == stg]
                g = c = 0
                for n in ds:
                    c = 0 if n else c + 1
                    g = max(g, c)
                gaps.append(f"{stg}:{g}d")
            print(f"  ✅ {label:<34} {msgs:>4} संदेश, शिखर {peak}/दिवस, खंड {' '.join(gaps)}")
    return all_ok


def coverage():
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
    from notification_policy import DELIVERY
    T = {**W1, **W2, **W3, **W4, **W5}
    files = ['Domain1_Rules_Ginger_v2.json'] + [f'Domain{i}_Rules_Ginger.json' for i in range(2, 15)]
    rules = {}
    for fn in files:
        d = json.loads(Path(fn).read_text(encoding='utf-8'))
        for r in d['rules']: rules[r['rule_id']] = r

    need = {rid for rid, r in rules.items()
            if r.get('decision_type') in {'AUTO_DECISION','SENSOR_ALERT','SCHEDULED_REMINDER','BLOCK'}}
    br = {rid for rid in need if rules[rid]['severity'] in ('blocking','red')}
    print()
    print(f"  triggers          : {len(T)}")
    print(f"  blocking/red      : {len(br & set(T))}/{len(br)}")
    print(f"  DSL लागणारे एकूण  : {len(need & set(T))}/{len(need)}")
    print(f"  delivery वर्ग नसलेले: {len([r for r in T if r not in DELIVERY])}")

    from expert_override import IMMUTABLE
    marked = {rid for rid, r in rules.items() if r.get('immutable')}
    if marked != set(IMMUTABLE):
        print(f"  ❌ immutable यादी जुळत नाही: JSON {len(marked)} vs code {len(IMMUTABLE)}")
        print(f"     फरक: {sorted(marked ^ set(IMMUTABLE))}")
        return False
    print(f"  immutable core    : {len(marked)} (JSON आणि code जुळतात)")
    ok = (br - set(T)) == set()
    if not ok:
        print(f"  ❌ trigger नसलेले blocking/red: {sorted(br - set(T))}")
    return ok


if __name__ == '__main__':
    print("═══ REGRESSION GATE ═══\n")
    results = [
        run('run_trigger_tests.py', 'trigger DSL + golden tests'),
        run('test_precedence.py',   'precedence + multi-diagnosis'),
        run('test_override.py',     'expert override + immutable core'),
        run('test_runner.py',       'daily runner + message quality'),
        run('test_persistence.py',  'state persistence across restarts'),
        run('test_runtime_loader.py','runtime loader — no build/KB drift'),
    ]
    results.append(coverage())
    results.append(season_assertions())

    print()
    if all(results):
        print("  ✅ सर्व gates पास — regenerate करण्यास तयार")
        sys.exit(0)
    print("  ❌ gate अपयशी — regenerate करू नका")
    sys.exit(1)
