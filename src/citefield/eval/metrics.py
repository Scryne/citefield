"""Value and location accuracy against labelled fields.

Rules carried over from the spikes (docs: spikes/s1-kaynak-esleme/SONUC.md, spikes/s2-guven/SONUC.md):
- Values compare by field kind. Labels keep the printed form ("1Prs", "1x") while a reader writes the meaning ("1"),
  so counts compare as numbers and amounts by their digits; everything else by alphanumeric normalisation.
- Location is scored only on fields whose value is right, with two criteria reported together. IoU >= 0.5 is strict
  and drops tiny one-digit boxes on drawing differences alone; centre-inside (3 px margin) is the primary criterion,
  and the only meaningful one where label boxes include the field's caption (FATURA).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from citefield.geometry import Box, center_inside, iou
from citefield.text import digits, normalize, quantity

IOU_THRESHOLD = 0.5
CENTER_MARGIN = 3.0

Kind = str  # "text" | "amount" | "count" | "date" | "id"


def values_equal(kind: Kind, pred: str, gold: str, *, containment: bool = False) -> bool:
    """`containment` accepts a prediction found inside the gold value; for label boxes that include the caption."""
    if kind == "count":
        q = quantity(pred)
        return q is not None and q == quantity(gold)
    if kind == "amount":
        d = digits(pred)
        return d is not None and d == digits(gold)
    a, b = normalize(pred), normalize(gold)
    return a == b or (containment and len(a) >= 3 and a in b)


@dataclass(frozen=True)
class Gold:
    field: str
    value: str
    box: Box


@dataclass(frozen=True)
class Pred:
    field: str
    value: str
    box: Box | None


@dataclass(frozen=True)
class Match:
    gold: Gold
    pred: Pred | None
    iou: float
    center: bool


def match(
    gold: Sequence[Gold], preds: Sequence[Pred], kind_of: Callable[[str], Kind], *, containment: bool = False
) -> list[Match]:
    """Pair each gold field with an unused prediction of the same name and an equal value. When a value repeats, the
    best-placed prediction wins, so two lines with the same price are not cross-matched."""
    used: set[int] = set()
    out: list[Match] = []
    for g in gold:
        cands = [
            (j, p)
            for j, p in enumerate(preds)
            if j not in used
            and p.field == g.field
            and values_equal(kind_of(g.field), p.value, g.value, containment=containment)
        ]
        if not cands:
            out.append(Match(g, None, 0.0, False))
            continue
        j, p = max(cands, key=lambda c: _placement(c[1].box, g.box))
        used.add(j)
        out.append(
            Match(
                g,
                p,
                iou(p.box, g.box) if p.box else 0.0,
                p.box is not None and center_inside(p.box, g.box, CENTER_MARGIN),
            )
        )
    return out


def _placement(box: Box | None, ref: Box) -> tuple[bool, float]:
    return (center_inside(box, ref, CENTER_MARGIN), iou(box, ref)) if box else (False, -1.0)


@dataclass(frozen=True)
class Summary:
    fields: int
    value_correct: int
    value_rate: float
    location_iou: float
    location_center: float


def summarize(matches: Sequence[Match]) -> Summary:
    right = [m for m in matches if m.pred is not None]

    def rate(x: int, n: int) -> float:
        return round(x / n, 3) if n else 0.0

    return Summary(
        len(matches),
        len(right),
        rate(len(right), len(matches)),
        rate(sum(m.iou >= IOU_THRESHOLD for m in right), len(right)),
        rate(sum(m.center for m in right), len(right)),
    )
