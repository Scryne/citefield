"""Approved data out: JSON, CSV and XLSX. Every row keeps its page and box, so a value stays traceable after export."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from citefield.store.models import DocumentRow

COLUMNS = ("field", "value", "item", "status", "page", "x0", "y0", "x1", "y1", "reasons")


def _rows(doc: DocumentRow) -> list[dict[str, Any]]:
    out = []
    for f in doc.fields:
        box: list[float | None] = list(f.box) if f.box else [None] * 4
        out.append(
            {
                "field": f.name,
                "value": f.value,
                "item": f.item,
                "status": f.status,
                "page": None if f.page is None else f.page + 1,
                "x0": box[0],
                "y0": box[1],
                "x1": box[2],
                "y1": box[3],
                "reasons": "; ".join(f.reasons),
            }
        )
    return out


def to_json(doc: DocumentRow) -> bytes:
    body = {
        "id": doc.id,
        "filename": doc.filename,
        "schema": doc.schema_name,
        "status": doc.status,
        "model": doc.model,
        "fields": [
            {
                "field": f.name,
                "value": f.value,
                "extracted_value": f.extracted_value,
                "item": f.item,
                "status": f.status,
                "reasons": f.reasons,
                "page": None if f.page is None else f.page + 1,
                "box": f.box,  # page pixels, origin top-left, at the page image's size
            }
            for f in doc.fields
        ],
        "pages": doc.pages,
        "rules": doc.rules,
        "possibly_missed": doc.possibly_missed,
    }
    return json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")


def _safe(v: Any) -> Any:
    """Spreadsheet formula injection: a value read from a document must not start a formula when opened. Signed
    numbers ("-3.00") are left alone; they are data, not formulas."""
    if not isinstance(v, str) or v[:1] not in ("=", "+", "-", "@", "\t", "\r"):
        return v
    if v[:1] in "+-" and v[1:].replace(",", "").replace(".", "").replace(" ", "").isdigit():
        return v
    return "'" + v


def to_csv(doc: DocumentRow) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    for r in _rows(doc):
        w.writerow({k: _safe(v) for k, v in r.items()})
    return ("﻿" + buf.getvalue()).encode("utf-8")  # BOM: Excel opens UTF-8 correctly


def to_xlsx(doc: DocumentRow) -> bytes:
    """Sheet "fields": one row per value. Sheet "items": line items pivoted, one row per item number."""
    import xlsxwriter

    buf = io.BytesIO()
    book = xlsxwriter.Workbook(buf, {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False})
    sheet = book.add_worksheet("fields")
    sheet.write_row(0, 0, COLUMNS)
    for i, r in enumerate(_rows(doc), 1):
        sheet.write_row(i, 0, [r[c] for c in COLUMNS])
    items: dict[int, dict[str, str]] = {}
    names: list[str] = []
    for f in doc.fields:
        if f.item is not None:
            items.setdefault(f.item, {})[f.name] = f.value
            if f.name not in names:
                names.append(f.name)
    if items:
        sheet2 = book.add_worksheet("items")
        sheet2.write_row(0, 0, ["item", *names])
        for row, (n, vals) in enumerate(sorted(items.items()), 1):
            sheet2.write_row(row, 0, [n, *[vals.get(c, "") for c in names]])
    book.close()
    return buf.getvalue()


FORMATS = {
    "json": (to_json, "application/json"),
    "csv": (to_csv, "text/csv; charset=utf-8"),
    "xlsx": (to_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
}
