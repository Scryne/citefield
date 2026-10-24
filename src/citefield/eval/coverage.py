"""Word coverage: the share of labelled value words that the ingest layer produced verbatim. A word the ingest layer
misses cannot be cited, so this is the ceiling on location accuracy.

Usage: python -m citefield.eval.coverage <data dir>"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path

from citefield.eval.datasets import Item, cord, fatura
from citefield.ingest import read_document
from citefield.text import normalize


def coverage(items: Iterable[Item]) -> tuple[int, int]:
    found = total = 0
    for it in items:
        words = {normalize(w.text) for w in read_document(it.image).words}
        for g in it.gold:
            for token in g.value.split():
                if normalize(token):
                    total += 1
                    found += normalize(token) in words
    return found, total


def main() -> None:
    data = Path(sys.argv[1])
    for name, items in (("cord", cord(data, 25)), ("fatura", fatura(data, 30))):
        f, t = coverage(items)
        print(f"{name}: {f}/{t} = {f / t:.1%}")


if __name__ == "__main__":
    main()
