"""Two reads of a document and the evidence behind every value.

Read 1 (K-Yol, S1): page images + OCR words with ids; the model cites the ids it read each value from.
Read 2 (K-İkinci okuma, S3): the same provider on the images alone. It is only compared with read 1 later (verify);
S3 found that a different input path caught real misreads (4/5) far better than a different model (2/5).

Boxes come only from cited words (K-Kanıt), checked by `cite_check`.

K-Satır (S3 hypothesis: line item fields must be cited inside their item's rows) was built and measured on 25 CORD
receipts and removed: it lowered location from 96.8% to 92.0% (Sonnet) and caught no wrong value. Quantities are printed
above the item name as often as below, and photographed receipts are skewed enough to break row grouping.
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


def cite_check(value: str, cited: list[int], words: dict[int, Word]) -> tuple[list[int], Citation]:
    """Citation check (S1): only cited words that occur inside the value go into the box, so a caption cited along
    with its value ("TOTAL 45,500") does not widen the box. When no cited word occurs in the value (OCR misread), the
    cited words are kept as the box, as measured in S1, but the citation is marked "outside" for review."""
    if not cited:
        return [], "missing"
    target = normalize(value)
    inside = [i for i in cited if normalize(words[i].text) and normalize(words[i].text) in target]
    if not inside:
        merged = [i for i in cited if _caption_merged(words[i].text, value)]
        return (merged, "exact") if merged else (cited, "outside")
    joined = "".join(normalize(words[i].text) for i in sorted(inside))
    return inside, "exact" if joined == target else "partial"


def _caption_merged(word: str, value: str) -> bool:
    """OCR often reads a caption and its value as one word ("Change:9,000", "SUB_TOTAL:1287.37"). The value counts as
    cited when it is the word's start or end and the boundary is punctuation, so "152,000" never cites "52,000"."""
    w, v = word.strip(), value.strip()
    if not v or len(w) <= len(v):
        return False
    return (w.endswith(v) and not w[-len(v) - 1].isalnum()) or (w.startswith(v) and not w[len(v)].isalnum())


def place(ids: list[int], words: dict[int, Word]) -> tuple[Box | None, int | None]:
    if not ids:
        return None, None
    page = Counter(words[i].page for i in ids).most_common(1)[0][0]
    return union(words[i].box for i in ids if words[i].page == page), page


def build(raw: list[dict[str, Any]], schema: Schema, doc: Document) -> tuple[list[Extracted], int]:
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
        evidence, citation = cite_check(value, cited, words)
        box, page = place(evidence, words)
        item = _int(a.get("item")) if spec.group else None
        out.append(
            Extracted(
                name, value, item, _float(a.get("confidence")), tuple(cited), tuple(evidence), citation, box, page
            )
        )
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
