"""Processing documents and applying review decisions, shared by the API, the worker and the CLI."""

from __future__ import annotations

import hashlib
import logging
import re
import threading
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select, update

from citefield.extract import cite_check, extract, place
from citefield.ingest import Document, Word
from citefield.ingest.cache import read_cached
from citefield.providers import Provider
from citefield.schema import Schema, load
from citefield.store import Store
from citefield.store.models import DocumentRow, FieldRow
from citefield.verify import verify

log = logging.getLogger("citefield")

MAX_UPLOAD = 25 * 1024 * 1024
ACCEPTED = (b"%PDF-", b"\x89PNG", b"\xff\xd8\xff", b"II*\x00", b"MM\x00*", b"RIFF")  # PDF, PNG, JPEG, TIFF, WebP


def accepted(data: bytes) -> bool:
    return data.startswith(ACCEPTED) and (not data.startswith(b"RIFF") or data[8:12] == b"WEBP")


class Service:
    def __init__(self, data_dir: Path, provider: Callable[[], Provider]) -> None:
        self.dir = data_dir
        self.store = Store(data_dir)
        self.provider = provider
        (data_dir / "uploads").mkdir(parents=True, exist_ok=True)

    def schema(self, name: str) -> Schema:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", name):
            raise ValueError("schema names are letters, digits, _ and -")
        custom = self.dir / "schemas" / f"{name}.json"
        return load(str(custom) if custom.exists() else name)

    def submit(self, filename: str, data: bytes, schema_name: str) -> str:
        if len(data) > MAX_UPLOAD:
            raise ValueError(f"file is larger than {MAX_UPLOAD // (1024 * 1024)} MB")
        if not accepted(data):
            raise ValueError("unsupported file type; send a PDF, PNG, JPEG, TIFF or WebP")
        self.schema(schema_name)  # fail now, not in the worker
        with self.store.session() as s:
            row = DocumentRow(filename=filename[:255], sha256=hashlib.sha256(data).hexdigest(), schema_name=schema_name)
            s.add(row)
            s.flush()
            (self.dir / "uploads" / row.id).write_bytes(data)
            return row.id

    def document(self, data: bytes) -> Document:
        return read_cached(data, self.dir / "ingest")

    def process(self, doc_id: str) -> None:
        with self.store.session() as s:
            row = s.get(DocumentRow, doc_id)
            if row is None:
                return
            schema_name = row.schema_name
        try:
            data = (self.dir / "uploads" / doc_id).read_bytes()
            doc = self.document(data)
            schema = self.schema(schema_name)
            provider = self.provider()
            ex = extract(doc, schema, provider)
            verdict = verify(ex, schema)
        except Exception as e:  # recorded on the document; the worker keeps going
            log.exception("processing %s failed", doc_id)
            with self.store.session() as s:
                s.execute(
                    update(DocumentRow).where(DocumentRow.id == doc_id).values(status="failed", error=str(e)[:2000])
                )
            return
        with self.store.session() as s:
            row = s.get(DocumentRow, doc_id)
            if row is None:
                return
            row.provider, row.model = provider.name, provider.model
            row.pages = [
                {"index": p.index, "width": p.width, "height": p.height, "source": p.source} for p in doc.pages
            ]
            row.words = [
                {"id": w.id, "text": w.text, "box": list(w.box), "page": w.page, "line": w.line} for w in doc.words
            ]
            row.rules = [asdict(r) for r in verdict.rules]
            row.possibly_missed = [
                {"field": m.field, "value": m.value, "item": m.item} for m in verdict.possibly_missed
            ]
            row.usage = {"reads": [asdict(r) | {"text": None} for r in ex.reads], "dropped_by_type_gate": ex.dropped}
            row.fields = [
                FieldRow(
                    position=i,
                    name=f.field,
                    value=f.value,
                    extracted_value=f.value,
                    item=f.item,
                    confidence=f.confidence,
                    evidence=list(f.evidence),
                    citation=f.citation,
                    box=list(f.box) if f.box else None,
                    page=f.page,
                    status=d.status,
                    reasons=d.reasons,
                )
                for i, (f, d) in enumerate(zip(ex.fields, verdict.decisions, strict=True))
            ]
            row.status, row.error = "ready", None

    def claim_next(self) -> str | None:
        with self.store.session() as s:
            doc_id = s.scalar(
                select(DocumentRow.id).where(DocumentRow.status == "queued").order_by(DocumentRow.created_at).limit(1)
            )
            if doc_id is None:
                return None
            claimed = s.execute(
                update(DocumentRow)
                .where(DocumentRow.id == doc_id, DocumentRow.status == "queued")
                .values(status="processing")
            )
            return doc_id if getattr(claimed, "rowcount", 0) else None  # 0 when another worker won the race

    def recover(self) -> None:
        """Documents left in processing by a crash or a stop go back to the queue."""
        with self.store.session() as s:
            s.execute(update(DocumentRow).where(DocumentRow.status == "processing").values(status="queued"))

    def review(
        self, doc_id: str, field_id: int, *, value: str | None, word_ids: list[int] | None, approve: bool
    ) -> FieldRow:
        with self.store.session() as s:
            f = s.get(FieldRow, field_id)
            if f is None or f.document_id != doc_id:
                raise KeyError(field_id)
            if word_ids is not None:
                words = {w["id"]: _word(w) for w in f.document.words}
                if any(i not in words for i in word_ids):
                    raise ValueError("unknown word id")
                ids, f.citation = cite_check(value if value is not None else f.value, word_ids, words)
                box, f.page = place(ids, words)
                f.evidence, f.box = ids, list(box) if box else None
            if value is not None and value != f.value:
                f.value, f.status = value, "corrected"
            elif approve or word_ids is not None:
                f.status = "approved" if f.value == f.extracted_value else "corrected"
            f.reviewed_at = datetime.now(UTC)
            return f


def _word(w: dict[str, Any]) -> Word:
    x0, y0, x1, y1 = w["box"]
    return Word(w["id"], w["text"], (x0, y0, x1, y1), w["page"], w["line"], "ocr")


class Worker(threading.Thread):
    def __init__(self, service: Service, idle: float = 0.5) -> None:
        super().__init__(daemon=True, name="citefield-worker")
        self.service, self.idle, self.stopped = service, idle, threading.Event()

    def run(self) -> None:
        self.service.recover()
        while not self.stopped.is_set():
            doc_id = self.service.claim_next()
            if doc_id is None:
                self.stopped.wait(self.idle)
            else:
                self.service.process(doc_id)

    def stop(self) -> None:
        self.stopped.set()
