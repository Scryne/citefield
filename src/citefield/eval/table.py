"""The README's accuracy table, generated from `citefield eval` reports so no number is typed by hand.

Usage: python -m citefield.eval.table <report.json>... [--readme README.md]
With --readme the table replaces the text between the eval markers in that file.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

START, END = "<!-- eval:start -->", "<!-- eval:end -->"
DATASET = {"cord": "CORD v2 receipts (photos)", "fatura": "FATURA invoices (synthetic)"}


def pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def row(r: dict[str, Any]) -> str:
    a, v, cost = r["accuracy"], r["review"], r["per_document"]["api_estimate_usd"]
    first, last = r.get("slice") or [0, r["documents"] - 1]
    model = {"sonnet": "claude-sonnet-5-5", "haiku": "claude-haiku-5-5"}.get(r["model"], r["model"])
    caught = f"{v['wrong_sent_to_review']}/{v['wrong']}" if v["wrong"] else "0/0"
    # FATURA is numbered by template (1-50), CORD by document index
    span = f"templates {first + 1}-{last + 1}" if r["dataset"] == "fatura" else f"docs {first}-{last}"
    return (
        f"| {DATASET.get(r['dataset'], r['dataset'])}, {span} | `{model}` | {pct(a['value_rate'])} "
        f"| {pct(a['location_center'])} | {pct(v['auto_share'])} | {pct(v['auto_error_rate'])} | {caught} "
        f"| ${cost.get(model, 0):.4f} |"
    )


def table(reports: list[dict[str, Any]]) -> str:
    head = (
        "| Data | Model | Values right | Box on the right words | Auto-approved | Errors among auto-approved "
        "| Wrong values sent to review | API cost / doc |\n|---|---|---|---|---|---|---|---|"
    )
    return "\n".join([head, *(row(r) for r in reports)])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("reports", nargs="+", type=Path)
    ap.add_argument("--readme", type=Path)
    a = ap.parse_args()
    text = table([json.loads(p.read_text("utf-8")) for p in a.reports])
    if a.readme:
        readme = a.readme.read_text("utf-8")
        if START not in readme or END not in readme:
            raise SystemExit(f"{a.readme} has no {START} … {END} block")
        block = f"{START}\n{text}\n{END}"
        a.readme.write_text(
            re.sub(re.escape(START) + ".*?" + re.escape(END), lambda _: block, readme, flags=re.S), "utf-8"
        )
    print(text)


if __name__ == "__main__":
    main()
