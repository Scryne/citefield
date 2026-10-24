"""The API end to end on a real PDF: upload, worker, review, export, delete. Only the model is faked."""

import csv
import io
import json
import re
import zipfile

import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen.canvas import Canvas

from citefield.api import create_app
from citefield.providers import ReadResult


def receipt_pdf() -> bytes:
    buf = io.BytesIO()
    c = Canvas(buf)
    c.setFont("Helvetica", 12)
    for y, text in ((760, "COFFEE HOUSE"), (720, "LATTE 4.50"), (700, "MUFFIN 3.00"), (660, "TOTAL 7.50")):
        c.drawString(72, y, text)
    c.save()
    return buf.getvalue()


class FakeProvider:
    """Reads the OCR word ids out of the prompt, like a model citing them. Second read: image only."""

    name, model = "fake", "fake-1"

    def __init__(self, total: str = "7.50", second_total: str = "7.50"):
        self.total, self.second_total = total, second_total

    def read(self, prompt, images, json_schema=None):
        if "OCR words" not in prompt:
            fields = [
                {"field": "merchant", "value": "COFFEE HOUSE"},
                {"field": "item.name", "value": "LATTE", "item": 1},
                {"field": "item.total", "value": "4.50", "item": 1},
                {"field": "item.name", "value": "MUFFIN", "item": 2},
                {"field": "item.total", "value": "3.00", "item": 2},
                {"field": "total", "value": self.second_total},
            ]
            return ReadResult(json.dumps({"fields": fields}), self.model)
        ids, seen = {}, set()
        for m in re.finditer(r"\[(\d+)\](\S+)", prompt):
            key = m.group(2) if m.group(2) not in seen else m.group(2) + "#2"
            seen.add(m.group(2))
            ids[key] = int(m.group(1))

        def f(field, value, words, item=None):
            return {
                "field": field,
                "value": value,
                "word_ids": [ids[w] for w in words],
                "item": item,
                "confidence": 0.99,
            }

        fields = [
            f("merchant", "COFFEE HOUSE", ["COFFEE", "HOUSE"]),
            f("item.name", "LATTE", ["LATTE"], 1),
            f("item.total", "4.50", ["4.50"], 1),
            f("item.name", "MUFFIN", ["MUFFIN"], 2),
            f("item.total", "3.00", ["3.00"], 2),
            f("total", self.total, ["TOTAL", "7.50"]),
        ]
        return ReadResult(json.dumps({"fields": fields}), self.model, 1000, 100)


def client(tmp_path, provider):
    app = create_app(tmp_path, lambda: provider, worker=False)
    return TestClient(app), app.state.service


def run_queue(service):
    while (doc_id := service.claim_next()) is not None:
        service.process(doc_id)


def upload(c, data=None, schema="receipt", name="r.pdf"):
    return c.post("/api/documents", files={"file": (name, data or receipt_pdf())}, data={"schema": schema})


def test_upload_process_review_export_delete(tmp_path):
    c, service = client(tmp_path, FakeProvider())
    r = upload(c)
    assert r.status_code == 202
    doc_id = r.json()["id"]
    assert c.get(f"/api/documents/{doc_id}").json()["status"] == "queued"
    run_queue(service)

    doc = c.get(f"/api/documents/{doc_id}").json()
    assert doc["status"] == "ready" and doc["pages"][0]["source"] == "pdf" and doc["to_review"] == 0
    fields = {(f["name"], f["item"]): f for f in doc["field_list"]}
    total = fields["total", None]
    assert total["status"] == "auto" and total["citation"] == "exact" and total["box"] is not None
    assert {r["outcome"] for r in doc["rules"]} >= {"holds"}

    page = c.get(f"/api/documents/{doc_id}/pages/1.png")
    assert page.status_code == 200 and page.content[:4] == b"\x89PNG"
    assert c.get(f"/api/documents/{doc_id}/pages/2.png").status_code == 404
    words = c.get(f"/api/documents/{doc_id}/words", params={"page": 1}).json()
    latte_price = next(w for w in words if w["text"] == "4.50")

    # reviewer corrects a value and re-cites the box from the page's words
    fid = fields["item.total", 2]["id"]
    r = c.patch(f"/api/documents/{doc_id}/fields/{fid}", json={"value": "4.50", "word_ids": [latte_price["id"]]})
    assert r.status_code == 200
    assert r.json()["status"] == "corrected" and r.json()["extracted_value"] == "3.00"
    assert r.json()["box"] == latte_price["box"]
    r = c.patch(f"/api/documents/{doc_id}/fields/{total['id']}", json={"approve": True})
    assert r.json()["status"] == "approved"
    assert c.patch(f"/api/documents/{doc_id}/fields/{fid}", json={"word_ids": [99999]}).status_code == 422

    body = json.loads(c.get(f"/api/documents/{doc_id}/export", params={"format": "json"}).content)
    assert {f["status"] for f in body["fields"]} >= {"corrected", "approved", "auto"}
    rows = list(
        csv.DictReader(io.StringIO(c.get(f"/api/documents/{doc_id}/export?format=csv").content.decode("utf-8-sig")))
    )
    assert rows[0].keys() >= {"field", "value", "page", "x0"} and rows[0]["page"] == "1"
    xlsx = c.get(f"/api/documents/{doc_id}/export?format=xlsx")
    sheets = zipfile.ZipFile(io.BytesIO(xlsx.content)).namelist()
    assert "xl/worksheets/sheet2.xml" in sheets  # the line items sheet

    assert c.delete(f"/api/documents/{doc_id}").status_code == 204
    assert c.get(f"/api/documents/{doc_id}").status_code == 404
    assert not (tmp_path / "uploads" / doc_id).exists()


def test_disagreeing_second_read_goes_to_review(tmp_path):
    c, service = client(tmp_path, FakeProvider(second_total="7.80"))
    doc_id = upload(c).json()["id"]
    run_queue(service)
    doc = c.get(f"/api/documents/{doc_id}").json()
    total = next(f for f in doc["field_list"] if f["name"] == "total")
    assert total["status"] == "review" and "second read" in total["reasons"][0] and doc["to_review"] == 1
    assert c.get("/api/documents").json()[0]["to_review"] == 1


@pytest.mark.parametrize(
    "data,schema,message",
    [
        (b"hello", "receipt", "unsupported file type"),
        (None, "nope", "unknown schema"),
        (None, "../etc", "schema names"),
    ],
)
def test_upload_validation(tmp_path, data, schema, message):
    c, _ = client(tmp_path, FakeProvider())
    r = upload(c, data, schema)
    assert r.status_code == 422 and message in r.json()["detail"]


def test_upload_size_limit(tmp_path, monkeypatch):
    monkeypatch.setattr("citefield.service.MAX_UPLOAD", 100)
    c, _ = client(tmp_path, FakeProvider())
    assert "larger than" in upload(c).json()["detail"]


def test_provider_failure_is_recorded_and_export_refused(tmp_path):
    class Broken(FakeProvider):
        def read(self, *a, **k):
            raise RuntimeError("rate limited")

    c, service = client(tmp_path, Broken())
    doc_id = upload(c).json()["id"]
    run_queue(service)
    doc = c.get(f"/api/documents/{doc_id}").json()
    assert doc["status"] == "failed" and "rate limited" in doc["error"]
    assert c.get(f"/api/documents/{doc_id}/export").status_code == 409

    # once the provider works again, the same upload is read without sending the file again
    service.provider = FakeProvider
    assert c.post(f"/api/documents/{doc_id}/retry").status_code == 202
    assert c.get(f"/api/documents/{doc_id}").json() | {"error": None} == c.get(f"/api/documents/{doc_id}").json()
    run_queue(service)
    assert c.get(f"/api/documents/{doc_id}").json()["status"] == "ready"
    assert c.post(f"/api/documents/{doc_id}/retry").status_code == 409


def test_summary_counts_and_stats(tmp_path):
    c, service = client(tmp_path, FakeProvider(second_total="7.80"))
    upload(c)
    run_queue(service)
    upload(c, data=b"%PDF-1.4 broken", name="broken.pdf")
    run_queue(service)

    ready = next(d for d in c.get("/api/documents").json() if d["filename"] == "r.pdf")
    assert ready["counts"] == {"auto": 5, "review": 1, "approved": 0, "corrected": 0}
    assert ready["page_count"] == 1 and ready["model"] == "fake-1" and ready["created_at"].endswith("+00:00")

    st = c.get("/api/stats", params={"days": 7}).json()
    assert st["documents"] == {"queued": 0, "processing": 0, "ready": 1, "failed": 1}
    assert st["fields"]["review"] == 1 and st["auto_share"] == 5 / 6
    assert st["triggers"] == {"second_read": 1}
    assert len(st["per_day"]) == 7 and st["per_day"][-1]["documents"] == 2
    assert st["schemas"] == {"receipt": 2}
    assert c.get("/api/stats", params={"days": 0}).status_code == 422


def test_settings_say_whether_a_key_is_set_but_never_show_it(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret-value")

    class Anthropicish(FakeProvider):
        name, model = "anthropic", "claude-sonnet-5-5"

    c, _ = client(tmp_path, Anthropicish())
    r = c.get("/api/settings")
    assert r.json()["api_key_set"] is True and r.json()["provider"] == "anthropic"
    assert "sk-ant-secret-value" not in r.text and r.json()["max_upload_mb"] == 25


def test_custom_schema_save_use_and_delete(tmp_path):
    c, service = client(tmp_path, FakeProvider())
    body = {
        "description": "coffee receipts",
        "fields": [
            {"name": "merchant", "kind": "text"},
            {"name": "item.name", "kind": "text", "group": "item", "anchor": True},
            {"name": "item.total", "kind": "amount", "group": "item"},
            {"name": "total", "kind": "amount"},
        ],
        "rules": [{"type": "sum", "of": "item.total", "equals": "total"}],
    }
    r = c.put("/api/schemas/coffee", json=body)
    assert r.status_code == 200 and r.json()["bundled"] is False
    saved = json.loads((tmp_path / "schemas" / "coffee.json").read_text("utf-8"))
    assert saved["name"] == "coffee" and saved["rules"] == [{"type": "sum", "equals": "total", "of": "item.total"}]
    assert "coffee" in [s["name"] for s in c.get("/api/schemas").json()]
    assert c.get("/api/schemas/coffee").json()["fields"][1] == {
        "name": "item.name",
        "kind": "text",
        "group": "item",
        "anchor": True,
    }

    doc_id = upload(c, schema="coffee").json()["id"]
    run_queue(service)
    assert c.get(f"/api/documents/{doc_id}").json()["rules"][0]["outcome"] == "holds"

    assert c.put("/api/schemas/invoice", json=body).status_code == 409
    assert c.put("/api/schemas/bad", json={"fields": []}).status_code == 422
    bad_rule = body | {"rules": [{"type": "sum", "of": "nope", "equals": "total"}]}
    assert "unknown fields" in c.put("/api/schemas/bad", json=bad_rule).json()["detail"]
    assert "schema names" in c.put("/api/schemas/bad.name", json=body).json()["detail"]
    assert c.put("/api/schemas/..%2Fx", json=body).status_code != 200  # never routed to the save
    assert c.delete("/api/schemas/receipt").status_code == 409
    assert c.delete("/api/schemas/coffee").status_code == 204
    assert c.get("/api/schemas/coffee").status_code == 404


def test_export_several_documents(tmp_path):
    c, service = client(tmp_path, FakeProvider())
    a = upload(c, name="a.pdf").json()["id"]
    b = upload(c, name="b.pdf").json()["id"]
    run_queue(service)
    r = c.get("/api/export", params={"ids": f"{a},{b},{a}", "format": "csv"})
    assert r.status_code == 200 and "2-documents" in r.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"))))
    assert {row["filename"] for row in rows} == {"a.pdf", "b.pdf"} and len(rows) == 12
    assert len(json.loads(c.get("/api/export", params={"ids": a, "format": "json"}).content)) == 1
    assert c.get("/api/export", params={"ids": f"{a},{b}"}).content[:2] == b"PK"  # xlsx by default

    queued = upload(c, name="c.pdf").json()["id"]
    assert "c.pdf" in c.get("/api/export", params={"ids": f"{a},{queued}"}).json()["detail"]
    assert c.get("/api/export", params={"ids": "missing"}).status_code == 404


def test_recover_requeues_interrupted_work(tmp_path):
    c, service = client(tmp_path, FakeProvider())
    doc_id = upload(c).json()["id"]
    assert service.claim_next() == doc_id and service.claim_next() is None
    service.recover()
    assert service.claim_next() == doc_id


def test_health_and_schemas(tmp_path):
    c, _ = client(tmp_path, FakeProvider())
    assert c.get("/api/health").json()["status"] == "ok"
    names = [s["name"] for s in c.get("/api/schemas").json()]
    assert names[:2] == ["invoice", "receipt"]


def test_csv_neutralises_formulas_but_keeps_signed_numbers():
    from citefield.export import _safe

    assert _safe("=HYPERLINK(1)") == "'=HYPERLINK(1)" and _safe("@SUM") == "'@SUM"
    assert _safe("-3.00") == "-3.00" and _safe("+1,250") == "+1,250" and _safe("LATTE") == "LATTE"
