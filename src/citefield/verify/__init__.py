"""Every extracted field is approved automatically or sent to review with its reasons (K-Güven, S2).

S2 could not show that a single confidence score separates right from wrong values, so there is no score here: a
field goes to review if any trigger fires, and the reviewer sees which ones did.

1. The second read (images only, no OCR words) disagrees or has no counterpart.
2. The model's own confidence is below the threshold.
3. An arithmetic rule the field takes part in does not hold, or its check digit fails.
4. The citation is missing, does not contain the value, or covers only part of it.
5. The same printed words are cited for two different fields (S2b: role confusion, e.g. card payment as cash).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from citefield.extract import Extracted, Extraction
from citefield.schema import Rule, Schema
from citefield.text import normalize, quantity
from citefield.verify.amounts import CHECKS, amount

MIN_CONFIDENCE = 0.9

CITATION_REASON = {
    "missing": "no words cited for this value",
    "outside": "the cited words do not contain this value",
    "partial": "the cited words cover only part of this value",
}


@dataclass
class Decision:
    status: Literal["auto", "review"] = "auto"
    reasons: list[str] = field(default_factory=list)

    def flag(self, reason: str) -> None:
        self.status = "review"
        if reason not in self.reasons:
            self.reasons.append(reason)


@dataclass(frozen=True)
class RuleResult:
    rule: str
    outcome: Literal["holds", "fails", "skipped"]
    detail: str = ""


@dataclass
class Verdict:
    decisions: list[Decision]  # one per Extraction.fields entry
    rules: list[RuleResult]
    possibly_missed: list[Extracted]  # values only the second read found

    @property
    def auto_share(self) -> float:
        return sum(d.status == "auto" for d in self.decisions) / len(self.decisions) if self.decisions else 0.0


def same_value(kind: str, a: str, b: str) -> bool:
    """Two reads of the same printed value. Amounts compare as numbers ("12.00" == "12"), counts as quantities."""
    if kind == "amount":
        x, y = amount(a), amount(b)
        return x is not None and x == y
    if kind == "count":
        q = quantity(a)
        return q is not None and q == quantity(b)
    return normalize(a) == normalize(b)


def _pair_second(
    fields: list[Extracted], second: list[Extracted], schema: Schema
) -> tuple[list[bool], list[Extracted]]:
    """Match each read-1 field with an unused read-2 entry of the same field and value. Item numbers are ignored:
    for equal values the pairing order cannot change which fields stay unmatched."""
    used: set[int] = set()
    found = []
    for f in fields:
        kind = schema.kind_of(f.field)
        cands = [
            j
            for j, s in enumerate(second)
            if j not in used and s.field == f.field and same_value(kind, f.value, s.value)
        ]
        if cands:
            used.add(cands[0])
        found.append(bool(cands))
    return found, [s for j, s in enumerate(second) if j not in used]


def _tolerance(x: Decimal) -> Decimal:
    return max(Decimal("0.01"), abs(x) * Decimal("0.0005"))


def _rule_text(r: Rule) -> str:
    if r.type == "sum":
        return f"sum of {r.of} = {r.equals}" + (f" (or {r.fallback})" if r.fallback else "")
    if r.type == "add":
        return " + ".join(r.terms) + "".join(f" - {m}" for m in r.minus) + f" = {r.equals}"
    return " x ".join(r.factors) + f" = {r.equals} (per item)"


def _check_rules(fields: list[Extracted], schema: Schema, decisions: list[Decision]) -> list[RuleResult]:
    values: dict[str, list[tuple[int, Decimal]]] = defaultdict(list)
    for i, f in enumerate(fields):
        if schema.kind_of(f.field) in ("amount", "count"):
            v = quantity(f.value) if schema.kind_of(f.field) == "count" else amount(f.value)
            if v is not None:
                values[f.field].append((i, Decimal(str(v)) if not isinstance(v, Decimal) else v))
    out = []

    def judge(text: str, lhs: Decimal, rhs: Decimal, involved: list[int]) -> None:
        if abs(lhs - rhs) <= _tolerance(rhs):
            out.append(RuleResult(text, "holds"))
            return
        detail = f"{lhs.normalize():f} != {rhs.normalize():f}"
        out.append(RuleResult(text, "fails", detail))
        for i in involved:
            decisions[i].flag(f"{text} does not hold ({detail})")

    for r in schema.rules:
        text = _rule_text(r)
        if r.type == "sum":
            items = values.get(r.of or "", [])
            target = values.get(r.equals)
            fallback = not target
            target = target or values.get(r.fallback or "")
            if not items or not target:
                out.append(RuleResult(text, "skipped"))
                continue
            lhs = sum((v for _, v in items), Decimal(0))
            alt = values.get(r.fallback or "") if not fallback else None
            if alt and abs(lhs - alt[0][1]) <= _tolerance(alt[0][1]):
                # tax-inclusive line prices add up to the total, not to the pre-tax subtotal (CORD, Indonesia)
                out.append(RuleResult(text, "holds", "matches the fallback"))
                continue
            if fallback and abs(lhs - target[0][1]) > _tolerance(target[0][1]):
                # without a subtotal, tax or service may sit between items and total: a match is evidence, a
                # mismatch is not (the false alarm this branch prevents was caught by a test, 2026-10-24)
                out.append(RuleResult(text, "skipped", "inconclusive against the fallback"))
                continue
            judge(text, lhs, target[0][1], [i for i, _ in items] + [target[0][0]])
        elif r.type == "add":
            first, target = values.get(r.terms[0]), values.get(r.equals)
            if not first or not target:
                out.append(RuleResult(text, "skipped"))
                continue
            plus = [x for t in r.terms for x in values.get(t, [])]
            less = [x for m in r.minus for x in values.get(m, [])]
            lhs = sum((v for _, v in plus), Decimal(0)) - sum((v for _, v in less), Decimal(0))
            judge(text, lhs, target[0][1], [i for i, _ in plus + less] + [target[0][0]])
        else:
            by_item: dict[int, dict[str, tuple[int, Decimal]]] = defaultdict(dict)
            for name in (*r.factors, r.equals):
                for i, v in values.get(name, []):
                    item = fields[i].item
                    if item is not None:
                        by_item[item].setdefault(name, (i, v))
            checked = False
            for parts in by_item.values():
                if all(n in parts for n in (*r.factors, r.equals)):
                    prod = Decimal(1)
                    for n in r.factors:
                        prod *= parts[n][1]
                    judge(text, prod, parts[r.equals][1], [parts[n][0] for n in (*r.factors, r.equals)])
                    checked = True
            if not checked:
                out.append(RuleResult(text, "skipped"))
    return out


def verify(ex: Extraction, schema: Schema, *, min_confidence: float = MIN_CONFIDENCE) -> Verdict:
    fields = ex.fields
    decisions = [Decision() for _ in fields]

    if ex.second or not fields:
        agreed, missed = _pair_second(fields, ex.second, schema)
        for d, ok in zip(decisions, agreed, strict=True):
            if not ok:
                d.flag("the second read (image only) does not agree")
    else:
        missed = []
        for d in decisions:
            d.flag("no second read")

    for d, f in zip(decisions, fields, strict=True):
        if f.confidence is not None and f.confidence < min_confidence:
            d.flag(f"model confidence {f.confidence:.2f} is below {min_confidence:.2f}")
        if f.citation in CITATION_REASON:
            d.flag(CITATION_REASON[f.citation])
        spec = schema.field(f.field)
        if spec and spec.check and not CHECKS[spec.check](f.value):
            d.flag(f"{spec.check.upper()} check digit fails")

    cited_by: dict[int, set[int]] = defaultdict(set)
    for i, f in enumerate(fields):
        for w in f.evidence:
            cited_by[w].add(i)
    for owners in cited_by.values():
        names = {fields[i].field for i in owners}
        if len(names) > 1:
            for i in owners:
                others = ", ".join(sorted(names - {fields[i].field}))
                decisions[i].flag(f"the same printed words are also cited as {others}")

    rules = _check_rules(fields, schema, decisions)
    return Verdict(decisions, rules, missed)
