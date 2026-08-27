#!/usr/bin/env python3
"""
AgroGuardian AI — Engine State Persistence
==========================================

A production bug, found by running the runner as it will actually be deployed.

The notification policy works by remembering what was already said. That state
lived in memory. In production the daily advisory is a scheduled job, so every
run is a fresh process — and every ONCE_UNTIL_RESOLVED rule fires again, every
EVENT rule loses its rising edge, and every WINDOW ladder resets.

Measured on five pre-season days:

    one long-lived process   :  5 messages
    a fresh process each day : 20 messages, the same four rules every day

The 998-to-92 improvement is real only while the process stays up. This module
makes it real after a restart.

What has to persist
-------------------
    notifier    first_issued, last_issued, issue_count, active EVENT set,
                resolved set, window_overdue
    overrides   the override table and its audit trail
    answered    which DIAGNOSTIC rules the farmer has responded to

Storage is a single JSON document per plot by default, because a farm is one
row and a file is easier to inspect than a table when something looks wrong.
The same interface has a PostgreSQL implementation for deployment.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

from expert_override import Override, OverrideStore
from notification_policy import Notifier

STATE_VERSION = 1


def _d(x): return x.isoformat() if isinstance(x, date) else x
def _p(x): return date.fromisoformat(x) if x else None


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def dump_notifier(n: Notifier) -> dict:
    return dict(
        first_issued={k: _d(v) for k, v in n.first_issued.items()},
        last_issued={k: _d(v) for k, v in n.last_issued.items()},
        issue_count=dict(n.issue_count),
        active=sorted(n.active),
        resolved=sorted(n.resolved),
        window_overdue=dict(n.window_overdue),
        suppressed_by_policy=dict(n.suppressed_by_policy),
        delivery_overrides={k: v for k, v in n.delivery.items()},
    )


def load_notifier(d: dict) -> Notifier:
    n = Notifier()
    if not d:
        return n
    n.first_issued = {k: _p(v) for k, v in d.get('first_issued', {}).items()}
    n.last_issued = {k: _p(v) for k, v in d.get('last_issued', {}).items()}
    n.issue_count.update(d.get('issue_count', {}))
    n.active = set(d.get('active', []))
    n.resolved = set(d.get('resolved', []))
    n.window_overdue.update(d.get('window_overdue', {}))
    n.suppressed_by_policy.update(d.get('suppressed_by_policy', {}))
    # delivery may carry expert overrides applied in an earlier run
    n.delivery.update(d.get('delivery_overrides', {}))
    return n


def dump_overrides(s: OverrideStore) -> dict:
    def one(o: Override):
        r = asdict(o)
        for k in ('created', 'expires', 'revoked'):
            r[k] = _d(r[k])
        return r
    return dict(items=[one(o) for o in s.items], audit=list(s.audit), seq=s._seq)


def load_overrides(d: dict, rules: dict) -> OverrideStore:
    s = OverrideStore(rules)
    if not d:
        return s
    for r in d.get('items', []):
        r = dict(r)
        for k in ('created', 'expires', 'revoked'):
            r[k] = _p(r[k])
        s.items.append(Override(**r))
    s.audit = list(d.get('audit', []))
    s._seq = d.get('seq', 0)
    return s


# ---------------------------------------------------------------------------
# Stores
# ---------------------------------------------------------------------------

class FileStateStore:
    """One JSON document per plot. Easy to read when something looks wrong."""

    def __init__(self, root='engine_state'):
        self.root = Path(root)
        self.root.mkdir(exist_ok=True)

    def _path(self, plot_id): return self.root / f"{plot_id}.json"

    def load(self, plot_id) -> dict:
        p = self._path(plot_id)
        if not p.exists():
            return {}
        d = json.loads(p.read_text(encoding='utf-8'))
        if d.get('version') != STATE_VERSION:
            # a version bump means the shape changed; start clean rather than
            # half-restore, and say so
            return {'_reset_reason': f"state version {d.get('version')} != {STATE_VERSION}"}
        return d

    def save(self, plot_id, notifier, overrides, answered, last_run):
        self._path(plot_id).write_text(json.dumps(dict(
            version=STATE_VERSION,
            plot_id=plot_id,
            last_run=_d(last_run),
            saved_at=datetime.now().isoformat(timespec='seconds'),
            notifier=dump_notifier(notifier),
            overrides=dump_overrides(overrides),
            answered=sorted(answered),
        ), ensure_ascii=False, indent=1), encoding='utf-8')


class SqliteStateStore:
    """Single-file database. Same interface, transactional, safe for concurrent runs."""

    DDL = """
    CREATE TABLE IF NOT EXISTS engine_state (
        plot_id   TEXT PRIMARY KEY,
        version   INTEGER NOT NULL,
        last_run  TEXT,
        saved_at  TEXT NOT NULL,
        payload   TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS advisory_log (
        plot_id   TEXT NOT NULL,
        day       TEXT NOT NULL,
        rule_id   TEXT NOT NULL,
        severity  TEXT NOT NULL,
        message   TEXT NOT NULL,
        PRIMARY KEY (plot_id, day, rule_id)
    );
    """

    def __init__(self, path='engine_state.db'):
        self.path = path
        with sqlite3.connect(self.path) as c:
            c.executescript(self.DDL)

    def load(self, plot_id) -> dict:
        with sqlite3.connect(self.path) as c:
            row = c.execute("SELECT version, payload FROM engine_state WHERE plot_id=?",
                            (plot_id,)).fetchone()
        if not row:
            return {}
        version, payload = row
        if version != STATE_VERSION:
            return {'_reset_reason': f"state version {version} != {STATE_VERSION}"}
        return json.loads(payload)

    def save(self, plot_id, notifier, overrides, answered, last_run):
        payload = json.dumps(dict(
            version=STATE_VERSION, plot_id=plot_id, last_run=_d(last_run),
            notifier=dump_notifier(notifier), overrides=dump_overrides(overrides),
            answered=sorted(answered)), ensure_ascii=False)
        with sqlite3.connect(self.path) as c:
            c.execute("""INSERT INTO engine_state (plot_id, version, last_run, saved_at, payload)
                         VALUES (?,?,?,?,?)
                         ON CONFLICT(plot_id) DO UPDATE SET
                           version=excluded.version, last_run=excluded.last_run,
                           saved_at=excluded.saved_at, payload=excluded.payload""",
                      (plot_id, STATE_VERSION, _d(last_run),
                       datetime.now().isoformat(timespec='seconds'), payload))

    def log_advisory(self, plot_id, day, messages):
        with sqlite3.connect(self.path) as c:
            c.executemany(
                """INSERT INTO advisory_log (plot_id, day, rule_id, severity, message)
                   VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING""",
                [(plot_id, _d(day), m.rule_id, m.severity, m.render()) for m in messages])

    def history(self, plot_id, limit=30):
        with sqlite3.connect(self.path) as c:
            return c.execute(
                """SELECT day, rule_id, severity FROM advisory_log
                   WHERE plot_id=? ORDER BY day DESC LIMIT ?""",
                (plot_id, limit)).fetchall()


# ---------------------------------------------------------------------------
# Persistent runner
# ---------------------------------------------------------------------------

class PersistentRunner:
    """A Runner that survives restarts. This is the deployable entry point."""

    def __init__(self, store=None, runner=None):
        from runner import Runner
        self.r = runner or Runner()
        self.store = store or FileStateStore()
        self.reset_reason = None

    def run_day(self, plot_id, ctx, day, *, cluster_id=None, attempted=None,
                answer_diagnostics=True, log=True):
        st = self.store.load(plot_id)
        self.reset_reason = st.pop('_reset_reason', None)

        self.r.notifier = load_notifier(st.get('notifier'))
        self.r.overrides = load_overrides(st.get('overrides'), self.r.rules)
        answered = set(st.get('answered', []))

        # a gap in runs is not a licence to replay. Record it so the caller
        # can tell the farmer the engine was down rather than silently catching up.
        last_run = _p(st.get('last_run'))
        gap = (day - last_run).days if last_run else None

        res = self.r.run(ctx, day, plot_id=plot_id, cluster_id=cluster_id,
                         answered=answered, attempted=attempted)

        if answer_diagnostics:
            for m in res['messages']:
                if self.r.rules[m.rule_id].get('decision_type') == 'DIAGNOSTIC':
                    answered.add(m.rule_id)

        self.store.save(plot_id, self.r.notifier, self.r.overrides, answered, day)
        if log and hasattr(self.store, 'log_advisory'):
            self.store.log_advisory(plot_id, day, res['messages'])

        res['gap_days'] = gap
        res['state_reset'] = self.reset_reason
        return res

    def create_override(self, plot_id, **kw):
        """Overrides must persist too, or the expert's change lasts one process."""
        st = self.store.load(plot_id)
        st.pop('_reset_reason', None)
        self.r.overrides = load_overrides(st.get('overrides'), self.r.rules)
        self.r.notifier = load_notifier(st.get('notifier'))
        ov = self.r.overrides.create(**kw)
        self.store.save(plot_id, self.r.notifier, self.r.overrides,
                        set(st.get('answered', [])), _p(st.get('last_run')) or date.today())
        return ov


if __name__ == '__main__':
    import shutil
    from datetime import timedelta

    from runner import demo_context

    shutil.rmtree('engine_state', ignore_errors=True)
    Path('engine_state.db').unlink(missing_ok=True)
    ctx = demo_context('preseason')

    print("═══ आधी: प्रत्येक दिवशी नवा process, स्थिती नाही ═══\n")
    from runner import Runner
    total = 0
    for i in range(5):
        d = date(2026, 3, 1) + timedelta(days=i)
        res = Runner().run(ctx, d)
        total += len(res['messages'])
        print(f"  {d}  {len(res['messages'])} संदेश")
    print(f"\n  एकूण {total} संदेश\n")

    print("═══ आता: प्रत्येक दिवशी नवा process, स्थिती साठवली ═══\n")
    total2 = 0
    for i in range(5):
        d = date(2026, 3, 1) + timedelta(days=i)
        pr = PersistentRunner(store=SqliteStateStore())   # fresh object each day
        res = pr.run_day('PLOT-77', ctx, d)
        total2 += len(res['messages'])
        ids = [m.rule_id for m in res['messages']]
        print(f"  {d}  {len(res['messages'])} संदेश  {ids}")
    print(f"\n  एकूण {total2} संदेश  ({total} वरून {total2})\n")

    print("═══ override सुद्धा टिकतो ═══\n")
    pr = PersistentRunner(store=SqliteStateStore())
    ov = pr.create_override('PLOT-77', rule_id='D02-DR-001', kind='THRESHOLD',
                            expert_id='AG-1', expert_name='डॉ. कदम',
                            rationale_mr='या भागातील काळी जमीन खोल आहे आणि खालचा थर वालुकामय आहे.',
                            scope='plot', scope_id='PLOT-77', day=date(2026, 3, 6),
                            new_threshold={'from': 12, 'to': 9})
    print(f"  तयार केला: {ov.override_id}")
    pr2 = PersistentRunner(store=SqliteStateStore())     # नवा process
    eff = load_overrides(SqliteStateStore().load('PLOT-77').get('overrides'),
                         pr2.r.rules).effective('D02-DR-001', date(2026, 3, 7), plot_id='PLOT-77')
    print(f"  restart नंतर: {len(eff['overrides'])} override सक्रिय")
    print(f"  अट: {eff['expr'][:76]}...")

    print("\n═══ engine बंद होता तर ते कळते ═══\n")
    pr = PersistentRunner(store=SqliteStateStore())
    res = pr.run_day('PLOT-77', ctx, date(2026, 3, 20))
    print(f"  शेवटच्या धावेपासून खंड: {res['gap_days']} दिवस")

    print("\n═══ सल्ल्याची नोंद ═══\n")
    for day, rid, sev in SqliteStateStore().history('PLOT-77', 8):
        print(f"  {day}  {sev:8s} {rid}")
