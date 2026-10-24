"""Axis-aligned boxes in page pixel coordinates: (x0, y0, x1, y1), origin top-left."""

from __future__ import annotations

from collections.abc import Iterable

Box = tuple[float, float, float, float]


def union(boxes: Iterable[Box]) -> Box:
    bs = list(boxes)
    if not bs:
        raise ValueError("union of no boxes")
    return (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))


def area(b: Box) -> float:
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def iou(a: Box, b: Box) -> float:
    inter = area((max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])))
    total = area(a) + area(b) - inter
    return inter / total if total > 0 else 0.0


def center_inside(box: Box, ref: Box, margin: float = 0.0) -> bool:
    """True if the center of `box` lies inside `ref` grown by `margin` on every side."""
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return ref[0] - margin <= cx <= ref[2] + margin and ref[1] - margin <= cy <= ref[3] + margin
