import json

import pytest

from citefield.extract import build, extract, output_schema, parse_fields, primary_prompt
from citefield.ingest.models import Document, Page, Word
from citefield.providers import ReadResult
from citefield.schema import load, parse

SCHEMA = load("receipt")

# A receipt laid out as OCR would see it: one printed row per line number.
ROWS = [
    ["COFFEE", "HOUSE"],  # 0
    ["1", "LATTE", "4.50"],  # 1
    ["1", "MUFFIN", "3.00"],  # 2
    ["2", "TEA", "4.50"],  # 3   repeats 4.50 on purpose
    ["TOTAL", "12.00"],  # 4
]


def _doc() -> Document:
    words, i = [], 0
    for line, row in enumerate(ROWS):
        x = 10.0
        for text in row:
            words.append(Word(i, text, (x, line * 30.0, x + 10 * len(text), line * 30.0 + 20), 0, line, "ocr"))
            x += 10 * len(text) + 15
            i += 1
    return Document("sha", [Page(0, 400, 200, b"png", "ocr", words)])


DOC = _doc()
ID = {(w.line, w.text): w.id for w in DOC.words}


def f(field, value, ids=(), item=None, confidence=0.9):
    return {"field": field, "value": value, "word_ids": list(ids), "item": item, "confidence": confidence}


def test_citation_drops_the_caption_and_boxes_the_value():
    (total,), _ = build([f("total", "12.00", [ID[4, "TOTAL"], ID[4, "12.00"]])], SCHEMA, DOC)
    assert total.citation == "exact" and total.evidence == (ID[4, "12.00"],)
    assert total.box == next(w.box for w in DOC.words if w.id == ID[4, "12.00"])


def test_misread_citation_is_kept_but_marked_outside():
    """OCR read 12.00 but the model reports 12.80 from the image: S1 keeps the cited box, the flag goes to review."""
    (total,), _ = build([f("total", "12.80", [ID[4, "12.00"]])], SCHEMA, DOC)
    assert total.citation == "outside" and total.box is not None


def test_missing_and_unknown_ids_give_no_box():
    (a, b), _ = build([f("total", "12.00", []), f("subtotal", "12.00", [999])], SCHEMA, DOC)
    assert a.citation == b.citation == "missing" and a.box is None and b.box is None


def test_partial_citation():
    (m,), _ = build([f("merchant", "COFFEE HOUSE", [ID[0, "COFFEE"]])], SCHEMA, DOC)
    assert m.citation == "partial"


def test_type_gate_drops_a_caption_given_as_amount():
    out, dropped = build([f("total", "TOTAL", [ID[4, "TOTAL"]])], SCHEMA, DOC)
    assert out == [] and dropped == 1


def test_unknown_fields_and_empty_values_are_ignored():
    out, _ = build([f("nonsense", "1"), f("total", "  ")], SCHEMA, DOC)
    assert out == []


def test_parse_fields_survives_prose_and_a_second_block():
    text = 'Here you go:\n{"fields": [{"field": "total", "value": "1"}]}\nand {"fields": []}'
    assert parse_fields(text) == [{"field": "total", "value": "1"}]
    assert parse_fields("no json") == [] and parse_fields('{"other": 1}') == []


def test_ids_given_as_strings_are_accepted():
    (t,), _ = build([f("total", "12.00", [str(ID[4, "12.00"])])], SCHEMA, DOC)
    assert t.evidence == (ID[4, "12.00"],)


def test_prompt_lists_word_ids_by_printed_row_and_marks_item_fields():
    p = primary_prompt(SCHEMA, DOC)
    assert f"[{ID[1, '1']}]1 [{ID[1, 'LATTE']}]LATTE [{ID[1, '4.50']}]4.50" in p
    assert "item.total (amount: line total) [line item field" in p and "- total (amount: grand total)\n" in p


def test_output_schema_is_strict():
    s = output_schema(SCHEMA, cited=True)["properties"]["fields"]["items"]
    assert s["additionalProperties"] is False and set(s["required"]) == {
        "field",
        "value",
        "item",
        "word_ids",
        "confidence",
    }
    assert "word_ids" not in output_schema(SCHEMA, cited=False)["properties"]["fields"]["items"]["properties"]


class FakeProvider:
    name, model = "fake", "fake-1"

    def __init__(self):
        self.prompts = []

    def read(self, prompt, images, json_schema=None):
        self.prompts.append(prompt)
        if "OCR words" in prompt:
            body = {"fields": [f("total", "12.00", [ID[4, "12.00"]])]}
        else:
            body = {"fields": [{"field": "total", "value": "12.00", "item": None}]}
        return ReadResult(json.dumps(body), self.model, 100, 20)


def test_extract_runs_both_reads_and_the_second_has_no_ocr():
    p = FakeProvider()
    ex = extract(DOC, SCHEMA, p)
    assert len(ex.reads) == 2 and sum("OCR words" in q for q in p.prompts) == 1
    assert ex.fields[0].box is not None and ex.second[0].value == "12.00" and ex.second[0].box is None


def test_schema_validation():
    with pytest.raises(ValueError, match="anchor"):
        parse({"fields": [{"name": "a", "group": "g"}]})
    with pytest.raises(ValueError, match="kind"):
        parse({"fields": [{"name": "a", "kind": "money"}]})
    with pytest.raises(ValueError, match="unique"):
        parse({"fields": [{"name": "a"}, {"name": "a"}]})
    for name in ("receipt", "invoice", "cord", "fatura"):
        assert load(name).fields


def test_caption_merged_into_the_value_word_counts_as_cited():
    words = [Word(0, "Change:9,000", (0, 0, 120, 20), 0, 0, "ocr"), Word(1, "152,000", (0, 30, 70, 50), 0, 1, "ocr")]
    doc = Document("sha", [Page(0, 200, 100, b"png", "ocr", words)])
    (change, price), _ = build([f("change", "9,000", [0]), f("item.total", "52,000", [1], item=1)], SCHEMA, doc)
    assert change.citation == "exact" and change.evidence == (0,)
    assert price.citation == "outside"  # a missing leading digit is a misread, not a caption
