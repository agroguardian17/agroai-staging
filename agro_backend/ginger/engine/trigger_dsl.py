#!/usr/bin/env python3
"""
AgroGuardian AI — Rule Trigger DSL
==================================

Turns a rule's English trigger sentence into a machine-evaluable expression.

Design constraints that came out of the knowledge base itself:

1. THREE-VALUED LOGIC. A field being absent is not the same as it being false.
   `calibration_done` unknown must NOT fire an alert that assumes it is false.
   Domain 12 D12-COLD-001 requires the engine to degrade and say so, so the
   evaluator returns TRUE / FALSE / UNKNOWN and the caller decides.

2. EVERY FIELD MUST BE DECLARED. Field names resolve against
   kb_farm_brain_fields. A typo is a parse error, not a silent false.

3. EXPLAINABLE. Domain 12 D12-POS-001 says the system must be able to say why.
   Evaluation returns a trace showing which sub-condition decided the outcome.

4. NO SIDE EFFECTS. A trigger only reads. Actions are separate.

Grammar
-------
    expr     := or_expr
    or_expr  := and_expr ( "OR" and_expr )*
    and_expr := not_expr ( "AND" not_expr )*
    not_expr := "NOT" not_expr | primary
    primary  := "(" expr ")" | comparison
    comparison :=
          field op value
        | field "IN" "[" value ("," value)* "]"
        | field "BETWEEN" value "AND" value
        | field "IS" ("NULL" | "NOT" "NULL" | "TRUE" | "FALSE")
        | "DURATION" "(" field ">" value ")" ">" value unit
        | "WITHIN" "(" field "," value unit ")"
        | "MONTH" "IN" "[" month ("," month)* "]"
        | "STAGE" "IN" "[" stage ("," stage)* "]"
    op       := ">" | ">=" | "<" | "<=" | "==" | "!="
    value    := number | quoted_string | field
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any

# ---------------------------------------------------------------------------
# Three-valued logic
# ---------------------------------------------------------------------------

class TV:
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"

    @staticmethod
    def and_(a, b):
        if a == TV.FALSE or b == TV.FALSE:
            return TV.FALSE
        if a == TV.UNKNOWN or b == TV.UNKNOWN:
            return TV.UNKNOWN
        return TV.TRUE

    @staticmethod
    def or_(a, b):
        if a == TV.TRUE or b == TV.TRUE:
            return TV.TRUE
        if a == TV.UNKNOWN or b == TV.UNKNOWN:
            return TV.UNKNOWN
        return TV.FALSE

    @staticmethod
    def not_(a):
        if a == TV.TRUE:
            return TV.FALSE
        if a == TV.FALSE:
            return TV.TRUE
        return TV.UNKNOWN


MONTHS = {m: i + 1 for i, m in enumerate(
    ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'])}
STAGES = ['G0','G1','G2','G3','G4','G5']


# ---------------------------------------------------------------------------
# Tokeniser
# ---------------------------------------------------------------------------

TOKEN_RE = re.compile(r"""
    (?P<ws>\s+)
  | (?P<num>-?\d+(?:\.\d+)?)
  | (?P<str>'[^']*')
  | (?P<op>>=|<=|!=|==|>|<)
  | (?P<punc>[(),\[\]])
  | (?P<word>[A-Za-z_][A-Za-z_0-9]*)
""", re.X)

KEYWORDS = {'AND','OR','NOT','IN','BETWEEN','IS','NULL','TRUE','FALSE',
            'DURATION','WITHIN','MONTH','STAGE','DAYS','HOURS'}


@dataclass
class Tok:
    kind: str
    val: Any
    pos: int


def tokenise(s: str) -> list[Tok]:
    toks, i = [], 0
    while i < len(s):
        m = TOKEN_RE.match(s, i)
        if not m:
            raise SyntaxError(f"unexpected character at {i}: {s[i]!r}")
        i = m.end()
        if m.lastgroup == 'ws':
            continue
        if m.lastgroup == 'num':
            toks.append(Tok('NUM', float(m.group()) if '.' in m.group() else int(m.group()), m.start()))
        elif m.lastgroup == 'str':
            toks.append(Tok('STR', m.group()[1:-1], m.start()))
        elif m.lastgroup == 'op':
            toks.append(Tok('OP', m.group(), m.start()))
        elif m.lastgroup == 'punc':
            toks.append(Tok(m.group(), m.group(), m.start()))
        else:
            w = m.group()
            toks.append(Tok('KW' if w.upper() in KEYWORDS else 'FIELD',
                            w.upper() if w.upper() in KEYWORDS else w, m.start()))
    return toks


# ---------------------------------------------------------------------------
# AST
# ---------------------------------------------------------------------------

class Node:
    def fields(self) -> set[str]:
        return set()

    def eval(self, ctx: dict, trace: list) -> str:
        raise NotImplementedError

    def to_str(self) -> str:
        raise NotImplementedError


@dataclass
class Cmp(Node):
    fld: str
    op: str
    val: Any

    def fields(self):
        return {self.fld} | ({self.val} if isinstance(self.val, FieldRef) and False else set())

    def eval(self, ctx, trace):
        left = ctx.get(self.fld)
        right = ctx.get(self.val.name) if isinstance(self.val, FieldRef) else self.val
        if left is None or right is None:
            trace.append((self.to_str(), TV.UNKNOWN, f"{self.fld}=None" if left is None else "rhs=None"))
            return TV.UNKNOWN
        try:
            r = {'>':  left >  right, '>=': left >= right, '<': left < right,
                 '<=': left <= right, '==': left == right, '!=': left != right}[self.op]
        except TypeError:
            trace.append((self.to_str(), TV.UNKNOWN, "type mismatch"))
            return TV.UNKNOWN
        out = TV.TRUE if r else TV.FALSE
        trace.append((self.to_str(), out, f"{self.fld}={left!r}"))
        return out

    def to_str(self):
        v = self.val.name if isinstance(self.val, FieldRef) else (
            f"'{self.val}'" if isinstance(self.val, str) else self.val)
        return f"{self.fld} {self.op} {v}"


@dataclass
class FieldRef:
    name: str


@dataclass
class InSet(Node):
    fld: str
    vals: list

    def fields(self):
        return {self.fld}

    def eval(self, ctx, trace):
        v = ctx.get(self.fld)
        if v is None:
            trace.append((self.to_str(), TV.UNKNOWN, f"{self.fld}=None"))
            return TV.UNKNOWN
        out = TV.TRUE if v in self.vals else TV.FALSE
        trace.append((self.to_str(), out, f"{self.fld}={v!r}"))
        return out

    def to_str(self):
        return f"{self.fld} IN [{', '.join(repr(x) for x in self.vals)}]"


@dataclass
class Between(Node):
    fld: str
    lo: Any
    hi: Any

    def fields(self):
        return {self.fld}

    def eval(self, ctx, trace):
        v = ctx.get(self.fld)
        if v is None:
            trace.append((self.to_str(), TV.UNKNOWN, f"{self.fld}=None"))
            return TV.UNKNOWN
        out = TV.TRUE if self.lo <= v <= self.hi else TV.FALSE
        trace.append((self.to_str(), out, f"{self.fld}={v}"))
        return out

    def to_str(self):
        return f"{self.fld} BETWEEN {self.lo} AND {self.hi}"


@dataclass
class IsCheck(Node):
    fld: str
    what: str          # NULL | NOT_NULL | TRUE | FALSE

    def fields(self):
        return {self.fld}

    def eval(self, ctx, trace):
        present = self.fld in ctx and ctx[self.fld] is not None
        v = ctx.get(self.fld)
        if self.what == 'NULL':
            out = TV.TRUE if not present else TV.FALSE
        elif self.what == 'NOT_NULL':
            out = TV.TRUE if present else TV.FALSE
        elif not present:
            out = TV.UNKNOWN
        elif self.what == 'TRUE':
            out = TV.TRUE if v is True else TV.FALSE
        else:
            out = TV.TRUE if v is False else TV.FALSE
        trace.append((self.to_str(), out, f"{self.fld}={v!r}"))
        return out

    def to_str(self):
        return f"{self.fld} IS {'NOT NULL' if self.what=='NOT_NULL' else self.what}"


@dataclass
class Duration(Node):
    """DURATION(field > x) > n HOURS — sustained condition, not an instant."""

    fld: str
    inner_op: str
    inner_val: Any
    n: Any
    unit: str

    def fields(self):
        return {self.fld, f"{self.fld}__duration"}

    def eval(self, ctx, trace):
        key = f"{self.fld}__duration"
        d = ctx.get(key)
        if d is None:
            trace.append((self.to_str(), TV.UNKNOWN, f"{key} not supplied"))
            return TV.UNKNOWN
        out = TV.TRUE if d > self.n else TV.FALSE
        trace.append((self.to_str(), out, f"{key}={d}"))
        return out

    def to_str(self):
        return f"DURATION({self.fld} {self.inner_op} {self.inner_val}) > {self.n} {self.unit}"


@dataclass
class Within(Node):
    """WITHIN(date_field, n DAYS) — is that date within n days from now.
    The engine supplies days_to_<X> alongside the date field."""

    fld: str
    n: Any
    unit: str

    def _key(self):
        base = self.fld.replace('_date', '')
        return f"days_to_{base}"

    def fields(self):
        return {self.fld, self._key()}

    def eval(self, ctx, trace):
        d = ctx.get(self._key())
        if d is None:
            trace.append((self.to_str(), TV.UNKNOWN, f"{self._key()} not supplied"))
            return TV.UNKNOWN
        out = TV.TRUE if 0 <= d <= self.n else TV.FALSE
        trace.append((self.to_str(), out, f"{self._key()}={d}"))
        return out

    def to_str(self):
        return f"WITHIN({self.fld}, {self.n} {self.unit})"


@dataclass
class Not(Node):
    inner: Node

    def fields(self):
        return self.inner.fields()

    def eval(self, ctx, trace):
        return TV.not_(self.inner.eval(ctx, trace))

    def to_str(self):
        return f"NOT ({self.inner.to_str()})"


@dataclass
class And(Node):
    parts: list

    def fields(self):
        return set().union(*(p.fields() for p in self.parts))

    def eval(self, ctx, trace):
        out = TV.TRUE
        for p in self.parts:
            out = TV.and_(out, p.eval(ctx, trace))
        return out

    def to_str(self):
        return " AND ".join(
            f"({p.to_str()})" if isinstance(p, Or) else p.to_str()
            for p in self.parts
        )


@dataclass
class Or(Node):
    parts: list

    def fields(self):
        return set().union(*(p.fields() for p in self.parts))

    def eval(self, ctx, trace):
        out = TV.FALSE
        for p in self.parts:
            out = TV.or_(out, p.eval(ctx, trace))
        return out

    def to_str(self):
        return " OR ".join(p.to_str() for p in self.parts)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class Parser:
    def __init__(self, toks, known_fields=None):
        self.t = toks
        self.i = 0
        self.known = known_fields

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def next(self):
        t = self.peek()
        if t is None:
            raise SyntaxError("unexpected end of expression")
        self.i += 1
        return t

    def accept(self, kind, val=None):
        t = self.peek()
        if t and t.kind == kind and (val is None or t.val == val):
            self.i += 1
            return t
        return None

    def expect(self, kind, val=None):
        t = self.accept(kind, val)
        if not t:
            raise SyntaxError(f"expected {val or kind} at token {self.i}")
        return t

    def parse(self):
        n = self.or_expr()
        if self.peek():
            raise SyntaxError(f"trailing tokens from position {self.peek().pos}")
        return n

    def or_expr(self):
        parts = [self.and_expr()]
        while self.accept('KW', 'OR'):
            parts.append(self.and_expr())
        return parts[0] if len(parts) == 1 else Or(parts)

    def and_expr(self):
        parts = [self.not_expr()]
        while self.accept('KW', 'AND'):
            parts.append(self.not_expr())
        return parts[0] if len(parts) == 1 else And(parts)

    def not_expr(self):
        if self.accept('KW', 'NOT'):
            return Not(self.not_expr())
        return self.primary()

    def primary(self):
        if self.accept('(', '('):
            n = self.or_expr()
            self.expect(')', ')')
            return n

        t = self.peek()
        if t and t.kind == 'KW' and t.val == 'DURATION':
            self.next()
            self.expect('(', '(')
            fld = self.field_name()
            op = self.expect('OP').val
            iv = self.value()
            self.expect(')', ')')
            self.expect('OP', '>')
            n = self.value()
            unit = self.expect('KW').val
            return Duration(fld, op, iv, n, unit)

        if t and t.kind == 'KW' and t.val == 'WITHIN':
            self.next()
            self.expect('(', '(')
            fld = self.field_name()
            self.expect(',', ',')
            n = self.value()
            unit = self.expect('KW').val
            self.expect(')', ')')
            return Within(fld, n, unit)

        if t and t.kind == 'KW' and t.val in ('MONTH', 'STAGE'):
            kw = self.next().val
            self.expect('KW', 'IN')
            vals = self.value_list()
            fld = 'current_month' if kw == 'MONTH' else 'current_stage'
            if kw == 'MONTH':
                vals = [MONTHS.get(str(v).upper()[:3], v) for v in vals]
            return InSet(fld, vals)

        fld = self.field_name()

        if self.accept('KW', 'IN'):
            return InSet(fld, self.value_list())
        if self.accept('KW', 'BETWEEN'):
            lo = self.value()
            self.expect('KW', 'AND')
            hi = self.value()
            return Between(fld, lo, hi)
        if self.accept('KW', 'IS'):
            if self.accept('KW', 'NOT'):
                self.expect('KW', 'NULL')
                return IsCheck(fld, 'NOT_NULL')
            kw = self.expect('KW').val
            if kw not in ('NULL', 'TRUE', 'FALSE'):
                raise SyntaxError(f"IS must be followed by NULL/TRUE/FALSE, got {kw}")
            return IsCheck(fld, kw)

        op = self.expect('OP').val
        return Cmp(fld, op, self.value())

    def field_name(self):
        t = self.expect('FIELD')
        if self.known is not None and t.val not in self.known:
            raise NameError(f"undeclared field: {t.val}")
        return t.val

    def value(self):
        t = self.next()
        if t.kind == 'NUM':
            return t.val
        if t.kind == 'STR':
            return t.val
        if t.kind == 'KW' and t.val in ('TRUE', 'FALSE'):
            return t.val == 'TRUE'
        if t.kind == 'FIELD':
            if self.known is not None and t.val not in self.known:
                return t.val                       # bare word acts as an enum literal
            return FieldRef(t.val)
        raise SyntaxError(f"expected a value at {t.pos}")

    def value_list(self):
        self.expect('[', '[')
        vals = [self.value()]
        while self.accept(',', ','):
            vals.append(self.value())
        self.expect(']', ']')
        return [v.name if isinstance(v, FieldRef) else v for v in vals]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse(expr: str, known_fields: set[str] | None = None) -> Node:
    return Parser(tokenise(expr), known_fields).parse()


@dataclass
class Result:
    outcome: str
    trace: list = dc_field(default_factory=list)
    missing: list = dc_field(default_factory=list)

    @property
    def fired(self):
        return self.outcome == TV.TRUE

    def why(self, lang='en'):
        """One line explaining the outcome — the deciding condition."""
        if self.outcome == TV.UNKNOWN:
            return ("माहिती अपुरी: " if lang == 'mr' else "insufficient data: ") + \
                   ", ".join(self.missing)
        decisive = [t for t in self.trace if t[1] == self.outcome]
        d = decisive[-1] if decisive else (self.trace[-1] if self.trace else ("", "", ""))
        return f"{d[0]}  [{d[2]}]"


def evaluate(node: Node, ctx: dict) -> Result:
    trace = []
    out = node.eval(ctx, trace)
    missing = sorted({t[2].split('=')[0] for t in trace
                      if (t[1] == TV.UNKNOWN and '=None' in t[2]) or 'not supplied' in t[2]})
    missing = [m.replace(' not supplied', '') for m in missing]
    return Result(out, trace, missing)


if __name__ == '__main__':
    known = {'saturation_hours', 'soil_moisture_vwc', 'vwc_saturation', 'current_stage',
             'calibration_done', 'dap', 'air_temp_max_c'}
    tests = [
        ("saturation_hours > 12 AND STAGE IN [G2, G3]", {'saturation_hours': 14, 'current_stage': 'G3'}),
        ("saturation_hours > 12 AND STAGE IN [G2, G3]", {'saturation_hours': 14}),
        ("calibration_done IS FALSE", {}),
        ("calibration_done IS FALSE", {'calibration_done': False}),
        ("dap BETWEEN 75 AND 90", {'dap': 82}),
        ("air_temp_max_c > 35 AND STAGE IN [G0, G1]", {'air_temp_max_c': 39, 'current_stage': 'G1'}),
    ]
    for e, ctx in tests:
        n = parse(e, known)
        r = evaluate(n, ctx)
        print(f"{r.outcome:8s} {e}")
        print(f"         ctx={ctx}  ->  {r.why()}")
