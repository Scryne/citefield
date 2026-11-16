"""Demo instance for screenshots and walkthroughs: the real app on a fresh data directory with fictional documents.

The reader is scripted (provider name "demo"): it cites the OCR word ids of values it was told, the way a model does,
so every box, check and review state below comes from the real pipeline. Two invoices and one receipt are processed;
on the first invoice the image-only second read disagrees on one unit price, so the review queue has work in it.
All companies, numbers and tax ids are invented.

Usage: python tests/demo_server.py <port>
"""

from __future__ import annotations

import io
import json
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import uvicorn
from reportlab.pdfgen.canvas import Canvas

from citefield.api import create_app
from citefield.providers import ReadResult

# One printed document: rows of (x, y, text, font size); fields: (name, value, tokens, item, second-read value or None).
Row = tuple[int, int, str, int]
Field = tuple[str, str, list[str], int | None, str | None]


@dataclass
class DemoDoc:
    filename: str
    schema: str
    marker: str  # a token only this document prints, to tell which one the primary read is looking at
    rows: list[Row]
    fields: list[Field] = field(default_factory=list)


INVOICE_LINES = [
    ("Recycled A4 paper, 5 reams", "12", "23.40", "280.80"),
    ("Gel pens, blue, box of 12", "8", "9.75", "78.00"),
    ("Archive boxes, kraft", "20", "4.15", "83.00"),
    ("Desk organiser, oak", "6", "31.90", "191.40"),
    ("Label printer tape", "10", "12.60", "126.00"),
]


def invoice_one() -> DemoDoc:
    rows: list[Row] = [
        (72, 770, "Harbor & Pine Stationery Ltd.", 16),
        (72, 752, "12 Quay Street, Port Avalon", 9),
        (72, 740, "VAT No. 4821937550", 9),
        (400, 770, "INVOICE", 16),
        (400, 752, "Invoice No. INV-2026-0418", 9),
        (400, 740, "Date 2026-11-03", 9),
        (400, 728, "Due 2026-12-03", 9),
        (72, 700, "Bill to", 9),
        (72, 686, "Atlas Field Labs", 11),
        (72, 672, "VAT No. 7302196648", 9),
        (72, 630, "Description", 9),
        (330, 630, "Qty", 9),
        (390, 630, "Unit", 9),
        (470, 630, "Amount", 9),
    ]
    fields: list[Field] = [
        ("seller.name", "Harbor & Pine Stationery Ltd.", ["Harbor", "&", "Pine", "Stationery", "Ltd."], None, None),
        ("seller.tax_id", "4821937550", ["4821937550"], None, None),
        ("buyer.name", "Atlas Field Labs", ["Atlas", "Field", "Labs"], None, None),
        ("buyer.tax_id", "7302196648", ["7302196648"], None, None),
        ("number", "INV-2026-0418", ["INV-2026-0418"], None, None),
        ("date", "2026-11-03", ["2026-11-03"], None, None),
        ("due_date", "2026-12-03", ["2026-12-03"], None, None),
        ("currency", "EUR", ["EUR"], None, None),
    ]
    y = 610
    for n, (desc, qty, unit, amount) in enumerate(INVOICE_LINES, start=1):
        rows += [(72, y, desc, 10), (330, y, qty, 10), (390, y, unit, 10), (470, y, amount, 10)]
        fields += [
            ("line.description", desc, desc.split(), n, None),
            ("line.quantity", qty, [qty], n, None),
            # The image-only read takes 4.15 for 4.75 on the third line: the one value a person has to look at.
            ("line.unit_price", unit, [unit], n, "4.75" if n == 3 else None),
            ("line.amount", amount, [amount], n, None),
        ]
        y -= 20
    rows += [
        (390, y - 20, "Subtotal", 10),
        (470, y - 20, "759.20", 10),
        (390, y - 38, "VAT 20%", 10),
        (470, y - 38, "151.84", 10),
        (390, y - 60, "Total EUR", 12),
        (470, y - 60, "911.04", 12),
        (72, y - 110, "Payment within 30 days. Thank you for your order.", 9),
    ]
    fields += [
        ("subtotal", "759.20", ["759.20"], None, None),
        ("tax", "151.84", ["151.84"], None, None),
        ("total", "911.04", ["911.04"], None, None),
    ]
    return DemoDoc("harbor-pine-INV-2026-0418.pdf", "invoice", "INV-2026-0418", rows, fields)


def invoice_two() -> DemoDoc:
    rows: list[Row] = [
        (72, 770, "Meridian Print Works", 16),
        (72, 752, "VAT No. 6619042873", 9),
        (400, 770, "INVOICE", 16),
        (400, 752, "Invoice No. MPW-7731", 9),
        (400, 740, "Date 2026-11-07", 9),
        (72, 700, "Bill to", 9),
        (72, 686, "Atlas Field Labs", 11),
        (72, 640, "Description", 9),
        (330, 640, "Qty", 9),
        (390, 640, "Unit", 9),
        (470, 640, "Amount", 9),
        (72, 620, "Field notebooks, 200 pages", 10),
        (330, 620, "40", 10),
        (390, 620, "6.50", 10),
        (470, 620, "260.00", 10),
        (72, 600, "Poster print, A1", 10),
        (330, 600, "4", 10),
        (390, 600, "18.00", 10),
        (470, 600, "72.00", 10),
        (390, 560, "Subtotal", 10),
        (470, 560, "332.00", 10),
        (390, 542, "VAT 20%", 10),
        (470, 542, "66.40", 10),
        (390, 520, "Total EUR", 12),
        (470, 520, "398.40", 12),
    ]
    fields: list[Field] = [
        ("seller.name", "Meridian Print Works", ["Meridian", "Print", "Works"], None, None),
        ("seller.tax_id", "6619042873", ["6619042873"], None, None),
        ("buyer.name", "Atlas Field Labs", ["Atlas", "Field", "Labs"], None, None),
        ("number", "MPW-7731", ["MPW-7731"], None, None),
        ("date", "2026-11-07", ["2026-11-07"], None, None),
        ("currency", "EUR", ["EUR"], None, None),
        ("line.description", "Field notebooks, 200 pages", ["Field", "notebooks,", "200", "pages"], 1, None),
        ("line.quantity", "40", ["40"], 1, None),
        ("line.unit_price", "6.50", ["6.50"], 1, None),
        ("line.amount", "260.00", ["260.00"], 1, None),
        ("line.description", "Poster print, A1", ["Poster", "print,", "A1"], 2, None),
        ("line.quantity", "4", ["4"], 2, None),
        ("line.unit_price", "18.00", ["18.00"], 2, None),
        ("line.amount", "72.00", ["72.00"], 2, None),
        ("subtotal", "332.00", ["332.00"], None, None),
        ("tax", "66.40", ["66.40"], None, None),
        ("total", "398.40", ["398.40"], None, None),
    ]
    return DemoDoc("meridian-MPW-7731.pdf", "invoice", "MPW-7731", rows, fields)


def receipt() -> DemoDoc:
    rows: list[Row] = [
        (72, 770, "COFFEE HOUSE", 14),
        (72, 740, "LATTE 4.50", 11),
        (72, 722, "MUFFIN 3.00", 11),
        (72, 690, "TOTAL 7.50", 12),
    ]
    fields: list[Field] = [
        ("merchant", "COFFEE HOUSE", ["COFFEE", "HOUSE"], None, None),
        ("item.name", "LATTE", ["LATTE"], 1, None),
        ("item.total", "4.50", ["4.50"], 1, None),
        ("item.name", "MUFFIN", ["MUFFIN"], 2, None),
        ("item.total", "3.00", ["3.00"], 2, None),
        ("total", "7.50", ["7.50"], None, None),
    ]
    return DemoDoc("coffee-house-receipt.pdf", "receipt", "MUFFIN", rows, fields)


def pdf(doc: DemoDoc) -> bytes:
    buf = io.BytesIO()
    c = Canvas(buf)
    c.setTitle(doc.filename)
    c.setAuthor("Citefield demo")
    for x, y, text, size in doc.rows:
        c.setFont("Helvetica-Bold" if size >= 14 else "Helvetica", size)
        c.drawString(x, y, text)
    c.save()
    return buf.getvalue()


class DemoProvider:
    """Cites the OCR word ids of each scripted value. The second read (images only) reports the scripted values,
    with the one planted disagreement."""

    name, model = "demo", "scripted"

    def __init__(self, docs: list[DemoDoc]):
        self.docs = docs
        self.current: DemoDoc | None = None

    def read(self, prompt, images, json_schema=None):
        if "OCR words" not in prompt:
            doc = self.current
            fields = [
                {"field": name, "value": second or value, "item": item}
                for name, value, _tokens, item, second in (doc.fields if doc else [])
            ]
            return ReadResult(json.dumps({"fields": fields}), self.model)
        words = [(int(m.group(1)), m.group(2)) for m in re.finditer(r"\[(\d+)\](\S+)", prompt)]
        tokens = [w for _, w in words]
        self.current = next(d for d in self.docs if d.marker in tokens)
        used: set[int] = set()

        def cite(sequence: list[str]) -> list[int]:
            for start in range(len(tokens) - len(sequence) + 1):
                if tokens[start : start + len(sequence)] == sequence and start not in used:
                    used.add(start)
                    return [words[start + k][0] for k in range(len(sequence))]
            raise ValueError(f"not printed: {sequence}")

        fields = [
            {"field": name, "value": value, "word_ids": cite(seq), "item": item, "confidence": 0.98}
            for name, value, seq, item, _second in self.current.fields
        ]
        return ReadResult(json.dumps({"fields": fields}), self.model)


def main() -> None:
    data = Path(tempfile.mkdtemp(prefix="citefield-demo-"))
    docs = [receipt(), invoice_two(), invoice_one()]
    provider = DemoProvider(docs)
    app = create_app(data, lambda: provider, worker=True)
    service = app.state.service
    for doc in docs:
        doc_id = service.submit(doc.filename, pdf(doc), doc.schema)
        service.claim_next()
        service.process(doc_id)
        print(f"DEMO_DOC {doc.filename} {doc_id}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=int(sys.argv[1]), log_level="warning")


if __name__ == "__main__":
    main()
