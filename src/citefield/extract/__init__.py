"""Two reads of a document and the evidence behind every value.

Read 1 (K-Yol, S1): page images + OCR words with ids; the model cites the ids it read each value from.
Read 2 (K-İkinci okuma, S3): the same provider on the images alone. It is only compared with read 1 later (verify);
S3 found that a different input path caught real misreads (4/5) far better than a different model (2/5).

Boxes come only from cited words (K-Kanıt). A citation that does not contain the value yields no box rather than a
guessed one, except for the S1 fallback described in `_evidence`.
"""

from __future__ import annotations

import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Literal

from citefield.geometry import Box, union
from citefield.ingest import Document, Word
from citefield.providers import Provider, ReadResult
from citefield.schema import Schema
from citefield.text import normalize

Citation = Literal["exact", "partial", "outside", "missing"]

RULES = (
    "Only extract values that are printed on the document. Copy them exactly as printed: do not fix spelling, do not "
    "infer values that are not printed. Never output a caption or label word (such as TOTAL, CASH, CHANGE) as a value."
)


@dataclass
class Extracted:
    field: str
    value: str
    item: int | None = None
    confidence: float | None = None
    cited: tuple[int, ...] = ()  # valid word ids as cited by the model
    evidence: tuple[int, ...] = ()  # ids the box is built from
    citation: Citation = "missing"
    box: Box | None = None
    page: int | None = None
    row: Literal["ok", "moved", "outside"] | None = None  # K-Satır outcome for group fields


@dataclass
class Extraction:
    fields: list[Extracted]
    second: list[Extracted]  # read 2: values only
    reads: list[ReadResult] = field(default_factory=list)
    dropped: int = 0  # values removed by the type gate


def _field_lines(schema: Schema) -> str:
    out = []
    for f in schema.fields:
        line = f"- {f.name} ({f.kind}{': ' + f.description if f.description else ''})"
        if f.group:
            line += f' [line item field: give "item", the 1-based number of the {f.group} it belongs to]'
        out.append(line)
    return "\n".join(out)


def _ocr_text(doc: Document) -> str:
    parts = []
    for page in doc.pages:
        rows: dict[int, list[Word]] = {}
        for w in page.words:
            rows.setdefault(w.line, []).append(w)
        parts.append(
            f"Page {page.index + 1}:\n" + "\n".join(" ".join(f"[{w.id}]{w.text}" for w in r) for r in rows.values())
        )
    return "\n".join(parts)


def _intro(schema: Schema) -> str:
    return f"You extract structured fields from a {schema.description or 'document'}. Fields:\n{_field_lines(schema)}"


def primary_prompt(schema: Schema, doc: Document) -> str:
    return (
        f"{_intro(schema)}\n{RULES}\n"
        "The page images are attached. Use the OCR words below to cite where each value is located. If OCR misread a "
        "character, give the value as printed in the image but still cite the word ids.\n"
        "OCR words, one printed line per row, each word prefixed with its id in brackets:\n"
        f"{_ocr_text(doc)}\n"
        'Return ONLY a JSON object: {"fields": [{"field": "<field name>", "value": "<value exactly as printed>", '
        '"word_ids": [<ids of the OCR words the value was read from>], "item": <item number for line item fields, else '
        'null>, "confidence": <0..1, how sure you are the value is correct>}]}. One entry per occurrence. Omit fields '
        "that are not printed."
    )


def secondary_prompt(schema: Schema) -> str:
    return (
        f"{_intro(schema)}\n{RULES}\nThe page images are attached.\n"
        'Return ONLY a JSON object: {"fields": [{"field": "<field name>", "value": "<value exactly as printed>", '
        '"item": <item number for line item fields, else null>}]}. One entry per occurrence. Omit fields that are not '
        "printed."
    )


def output_schema(schema: Schema, cited: bool) -> dict[str, Any]:
    """JSON schema for providers that enforce structured output."""
    props: dict[str, Any] = {
        "field": {"type": "string", "enum": [f.name for f in schema.fields]},
        "value": {"type": "string"},
        "item": {"type": ["integer", "null"]},
    }
    if cited:
        props["word_ids"] = {"type": "array", "items": {"type": "integer"}}
        props["confidence"] = {"type": "number"}
    entry = {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}
    return {
        "type": "object",
        "properties": {"fields": {"type": "array", "items": entry}},
        "required": ["fields"],
        "additionalProperties": False,
    }


def parse_fields(text: str) -> list[dict[str, Any]]:
    """The first JSON object with a "fields" list; survives prose or a second block after it (S1, fatura-04)."""
    dec = json.JSONDecoder()
    i = text.find("{")
    while i != -1:
        try:
            obj, _ = dec.raw_decode(text, i)
            if isinstance(obj, dict) and isinstance(obj.get("fields"), list):
                return [f for f in obj["fields"] if isinstance(f, dict)]
        except json.JSONDecodeError:
            pass
        i = text.find("{", i + 1)
    return []


def _int(v: Any) -> int | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.strip().isdigit():
        return int(v)
    return None


def _float(v: Any) -> float | None:
    try:
        return float(v) if v is not None and not isinstance(v, bool) else None
    except (TypeError, ValueError):
        return None


def type_gate(kind: str, value: str) -> bool:
    """An amount or a count without a digit is a caption read as a value (S3: "TOTAL" as total)."""
    return kind not in ("amount", "count") or any(ch.isdigit() for ch in value)


def _evidence(value: str, cited: list[int], words: dict[int, Word]) -> tuple[list[int], Citation]:
    """Citation check (S1): only cited words that occur inside the value go into the box, so a caption cited along
    with its value ("TOTAL 45,500") does not widen the box. When no cited word occurs in the value (OCR misread), the
    cited words are kept as the box, as measured in S1, but the citation is marked "outside" for review."""
    if not cited:
        return [], "missing"
    target = normalize(value)
    inside = [i for i in cited if normalize(words[i].text) and normalize(words[i].text) in target]
    if not inside:
        return cited, "outside"
    joined = "".join(normalize(words[i].text) for i in sorted(inside))
    return inside, "exact" if joined == target else "partial"


def _place(ids: list[int], words: dict[int, Word]) -> tuple[Box | None, int | None]:
    if not ids:
        return None, None
    page = Counter(words[i].page for i in ids).most_common(1)[0][0]
    return union(words[i].box for i in ids if words[i].page == page), page


def _apply_rows(fields: list[Extracted], schema: Schema, doc: Document) -> None:
    """K-Satır (S3 hypothesis): a line item field must be cited inside its item's rows, which run from the item's
    anchor (its name) to the row before the next item's anchor. A citation outside is moved to a unique matching word
    run inside the rows; if there is none or several, the box is withdrawn."""
    words = {w.id: w for w in doc.words}
    by_line: dict[int, list[Word]] = {}
    for w in doc.words:
        by_line.setdefault(w.line, []).append(w)
    for group in {f.group for f in schema.fields if f.group}:
        anchor = next(f.name for f in schema.fields if f.group == group and f.anchor)
        starts: dict[int, int] = {}
        for e in fields:
            if e.field == anchor and e.item is not None and e.evidence:
                starts[e.item] = min(starts.get(e.item, 10**9), min(words[i].line for i in e.evidence))
        order = sorted(set(starts.values()))
        last_line = max(by_line, default=0)
        for e in fields:
            spec = schema.field(e.field)
            if spec is None or spec.group != group or spec.anchor or e.item not in starts:
                continue
            first = starts[e.item]
            later = [s for s in order if s > first]
            rows = range(first, (later[0] - 1 if later else last_line) + 1)
            if e.evidence and all(words[i].line in rows for i in e.evidence):
                e.row = "ok"
                continue
            runs = _matching_runs(e.value, [by_line.get(r, []) for r in rows])
            if len(runs) == 1:
                e.evidence, e.row = tuple(runs[0]), "moved"
                e.box, e.page = _place(list(runs[0]), words)
            else:
                e.evidence, e.row, e.box, e.page = (), "outside", None, None


def _matching_runs(value: str, rows: list[list[Word]], longest: int = 4) -> list[list[int]]:
    target = normalize(value)
    runs = []
    for row in rows:
        for a in range(len(row)):
            joined = ""
            for b in range(a, min(a + longest, len(row))):
                joined += normalize(row[b].text)
                if joined == target:
                    runs.append([w.id for w in row[a : b + 1]])
                if len(joined) >= len(target):
                    break
    return runs


def build(raw: list[dict[str, Any]], schema: Schema, doc: Document, rows: bool = True) -> tuple[list[Extracted], int]:
    words = {w.id: w for w in doc.words}
    out, dropped = [], 0
    for a in raw:
        name, value = str(a.get("field", "")), str(a.get("value", "")).strip()
        spec = schema.field(name)
        if spec is None or not value:
            continue
        if not type_gate(spec.kind, value):
            dropped += 1
            continue
        cited = [i for i in (_int(x) for x in a.get("word_ids") or []) if i is not None and i in words]
        evidence, citation = _evidence(value, cited, words)
        box, page = _place(evidence, words)
        item = _int(a.get("item")) if spec.group else None
        out.append(
            Extracted(
                name, value, item, _float(a.get("confidence")), tuple(cited), tuple(evidence), citation, box, page
            )
        )
    if rows:
        _apply_rows(out, schema, doc)
    return out, dropped


def extract(
    doc: Document, schema: Schema, provider: Provider, *, second: bool = True, structured: bool = False
) -> Extraction:
    images = [p.image for p in doc.pages]
    jobs = [(primary_prompt(schema, doc), output_schema(schema, True) if structured else None)]
    if second:
        jobs.append((secondary_prompt(schema), output_schema(schema, False) if structured else None))
    with ThreadPoolExecutor(len(jobs)) as pool:
        reads = list(pool.map(lambda j: provider.read(j[0], images, j[1]), jobs))
    fields, dropped = build(parse_fields(reads[0].text), schema, doc)
    others: list[Extracted] = []
    if second:
        for a in parse_fields(reads[1].text):
            spec = schema.field(str(a.get("field", "")))
            value = str(a.get("value", "")).strip()
            if spec and value and type_gate(spec.kind, value):
                others.append(Extracted(spec.name, value, _int(a.get("item")) if spec.group else None))
    return Extraction(fields, others, reads, dropped)
