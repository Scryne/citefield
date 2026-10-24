"""REST API and the bundled review UI. v1 is single-user and binds to localhost by default: there is no login."""

from __future__ import annotations

import json
import os
from collections import Counter
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from importlib import resources
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import Body, FastAPI, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import func, select

from citefield import __version__, providers
from citefield.export import FORMATS, MANY_FORMATS
from citefield.providers import Provider
from citefield.schema import CHECKS, KINDS, Schema, parse
from citefield.service import ACCEPTED_TYPES, MAX_UPLOAD, Service, Worker
from citefield.store.models import DocumentRow, FieldRow
from citefield.verify import trigger

BUNDLED_SCHEMAS = ("invoice", "receipt")


class FieldOut(BaseModel):
    id: int
    name: str
    value: str
    extracted_value: str
    item: int | None
    confidence: float | None
    citation: str
    evidence: list[int]
    box: list[float] | None
    page: int | None
    status: str
    reasons: list[str]


class DocumentSummary(BaseModel):
    id: str
    filename: str
    schema_name: str
    status: str
    error: str | None
    to_review: int
    fields: int
    counts: dict[str, int]  # fields by status: auto, review, approved, corrected
    page_count: int
    model: str | None
    created_at: str
    updated_at: str


class DocumentOut(DocumentSummary):
    pages: list[dict[str, Any]]
    rules: list[dict[str, Any]]
    possibly_missed: list[dict[str, Any]]
    field_list: list[FieldOut]


class FieldPatch(BaseModel):
    value: str | None = None
    word_ids: list[int] | None = None
    approve: bool = False


def _field(f: FieldRow) -> FieldOut:
    return FieldOut(
        id=f.id,
        name=f.name,
        value=f.value,
        extracted_value=f.extracted_value,
        item=f.item,
        confidence=f.confidence,
        citation=f.citation,
        evidence=f.evidence,
        box=f.box,
        page=f.page,
        status=f.status,
        reasons=f.reasons,
    )


def _utc(t: datetime) -> datetime:
    # SQLite hands datetimes back without their zone; they are stored in UTC
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def _summary(d: DocumentRow) -> dict[str, Any]:
    counts = Counter(f.status for f in d.fields)
    return {
        "id": d.id,
        "filename": d.filename,
        "schema_name": d.schema_name,
        "status": d.status,
        "error": d.error,
        "to_review": counts["review"],
        "fields": len(d.fields),
        "counts": {k: counts[k] for k in ("auto", "review", "approved", "corrected")},
        "page_count": len(d.pages),
        "model": d.model,
        "created_at": _utc(d.created_at).isoformat(),
        "updated_at": _utc(d.updated_at).isoformat(),
    }


def _schema(name: str, sc: Schema, bundled: bool) -> dict[str, Any]:
    """A schema as JSON, leaving out unset options, so what the API returns is what a user would write."""
    return {
        "name": name,
        "description": sc.description,
        "bundled": bundled,
        "fields": [
            {k: v for k, v in vars(f).items() if k in ("name", "kind") or v not in (None, "", False)} for f in sc.fields
        ],
        "rules": [
            {k: list(v) if isinstance(v, tuple) else v for k, v in vars(r).items() if v not in (None, ())}
            for r in sc.rules
        ],
    }


def default_provider() -> Callable[[], Provider]:
    name = os.environ.get("CITEFIELD_PROVIDER", "anthropic")
    model = os.environ.get("CITEFIELD_MODEL") or None
    base_url = os.environ.get("CITEFIELD_BASE_URL") or None
    extra = {"base_url": base_url} if base_url else {}
    return lambda: providers.get(name, model, **extra)


def create_app(data_dir: Path, provider: Callable[[], Provider] | None = None, *, worker: bool = True) -> FastAPI:
    service = Service(data_dir, provider or default_provider())
    background = Worker(service) if worker else None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if background:
            background.start()
        yield
        if background:
            background.stop()

    app = FastAPI(title="Citefield", version=__version__, lifespan=lifespan)
    app.state.service = service

    def get_doc(s: Any, doc_id: str) -> DocumentRow:
        d = s.get(DocumentRow, doc_id)
        if d is None:
            raise HTTPException(404, "document not found")
        return d  # type: ignore[no-any-return]

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        with service.store.session() as s:
            queued = s.scalar(select(func.count()).where(DocumentRow.status.in_(("queued", "processing"))))
        return {"status": "ok", "version": __version__, "queued": queued}

    @app.get("/api/settings")
    def settings() -> dict[str, Any]:
        """What this instance runs with, for the settings screen. Never a key: only whether one is set."""
        name = os.environ.get("CITEFIELD_PROVIDER", "anthropic")
        try:
            p = service.provider()
            model: str | None = p.model
            name = p.name
        except Exception:  # a missing key or package must not take the settings screen down with it
            model = os.environ.get("CITEFIELD_MODEL") or None
        key = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}.get(name)
        return {
            "version": __version__,
            "provider": name,
            "model": model,
            "base_url": os.environ.get("CITEFIELD_BASE_URL") or None,
            "api_key_env": key,
            "api_key_set": bool(key and os.environ.get(key)),
            "data_dir": str(data_dir),
            "schemas_dir": str(data_dir / "schemas"),
            "max_upload_mb": MAX_UPLOAD // (1024 * 1024),
            "accepted_types": list(ACCEPTED_TYPES),
            "worker": bool(background and background.is_alive()),
            "kinds": list(KINDS),
            "checks": list(CHECKS),
        }

    @app.get("/api/stats")
    def stats(days: Annotated[int, Query(ge=1, le=90)] = 14) -> dict[str, Any]:
        """Totals for the overview: documents and fields by status, why fields went to review, documents per day."""
        today = datetime.now(UTC).date()
        start = today - timedelta(days=days - 1)
        with service.store.session() as s:
            docs = s.scalars(select(DocumentRow)).all()
            by_status = Counter(d.status for d in docs)
            fields = Counter(f.status for d in docs for f in d.fields)
            # once per check that sent a field to review, also after a person cleared it: the reasons stay
            triggers = Counter(t for d in docs for f in d.fields for t in {trigger(r) for r in f.reasons})
            per_day = Counter(_utc(d.created_at).date() for d in docs)
            seconds = [sum(r.get("seconds", 0) for r in d.usage.get("reads", [])) for d in docs if d.status == "ready"]
            schemas = Counter(d.schema_name for d in docs)
        checked = sum(fields.values())
        return {
            "documents": {k: by_status[k] for k in ("queued", "processing", "ready", "failed")},
            "fields": {k: fields[k] for k in ("auto", "review", "approved", "corrected")},
            "auto_share": fields["auto"] / checked if checked else None,
            "triggers": dict(triggers.most_common()),
            "per_day": [
                {"date": (start + timedelta(days=i)).isoformat(), "documents": per_day[start + timedelta(days=i)]}
                for i in range(days)
            ],
            "seconds_per_document": sum(seconds) / len(seconds) if seconds else None,
            "schemas": dict(schemas.most_common()),
        }

    def custom_schema(name: str) -> Path:
        try:
            service.schema_name_ok(name)
        except ValueError as e:
            raise HTTPException(422, str(e)) from None
        if name in BUNDLED_SCHEMAS:
            raise HTTPException(409, f"{name!r} is a bundled schema; save yours under another name")
        return data_dir / "schemas" / f"{name}.json"

    @app.get("/api/schemas")
    def schemas() -> list[dict[str, Any]]:
        names = list(BUNDLED_SCHEMAS) + sorted(p.stem for p in (data_dir / "schemas").glob("*.json"))
        return [_schema(n, service.schema(n), n in BUNDLED_SCHEMAS) for n in names]

    @app.get("/api/schemas/{name}")
    def schema(name: str) -> dict[str, Any]:
        try:
            return _schema(name, service.schema(name), name in BUNDLED_SCHEMAS)
        except (FileNotFoundError, ValueError):
            raise HTTPException(404, "schema not found") from None

    @app.put("/api/schemas/{name}")
    def save_schema(name: str, body: Annotated[dict[str, Any], Body()]) -> dict[str, Any]:
        path = custom_schema(name)
        try:
            sc = parse(body | {"name": name})
        except (KeyError, TypeError, ValueError, AttributeError) as e:
            raise HTTPException(422, f"invalid schema: {e}") from None
        out = _schema(name, sc, False)
        path.parent.mkdir(parents=True, exist_ok=True)
        saved = {k: v for k, v in out.items() if k != "bundled"}
        path.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + "\n", "utf-8")
        return out

    @app.delete("/api/schemas/{name}", status_code=204)
    def delete_schema(name: str) -> None:
        path = custom_schema(name)
        if not path.exists():
            raise HTTPException(404, "schema not found")
        path.unlink()

    @app.post("/api/documents", status_code=202)
    async def upload(
        file: Annotated[UploadFile, File()], schema_name: Annotated[str, Form(alias="schema")] = "invoice"
    ) -> dict[str, str]:
        data = await file.read()
        try:
            doc_id = service.submit(file.filename or "document", data, schema_name)
        except FileNotFoundError:
            raise HTTPException(422, f"unknown schema {schema_name!r}") from None
        except ValueError as e:
            raise HTTPException(422, str(e)) from None
        return {"id": doc_id}

    @app.get("/api/documents", response_model=list[DocumentSummary])
    def documents() -> list[dict[str, Any]]:
        with service.store.session() as s:
            rows = s.scalars(select(DocumentRow).order_by(DocumentRow.created_at.desc())).all()
            return [_summary(d) for d in rows]

    @app.get("/api/documents/{doc_id}", response_model=DocumentOut)
    def document(doc_id: str) -> dict[str, Any]:
        with service.store.session() as s:
            d = get_doc(s, doc_id)
            return _summary(d) | {
                "pages": d.pages,
                "rules": d.rules,
                "possibly_missed": d.possibly_missed,
                "field_list": [_field(f) for f in d.fields],
            }

    @app.post("/api/documents/{doc_id}/retry", status_code=202)
    def retry(doc_id: str) -> dict[str, str]:
        """A failed document goes back to the queue, for example after the provider settings were fixed."""
        with service.store.session() as s:
            d = get_doc(s, doc_id)
            if d.status != "failed":
                raise HTTPException(409, f"document is {d.status}")
            d.status, d.error = "queued", None
        return {"id": doc_id}

    @app.get("/api/documents/{doc_id}/pages/{page}.png")
    def page_image(doc_id: str, page: int) -> Response:
        with service.store.session() as s:
            get_doc(s, doc_id)
        data = (data_dir / "uploads" / doc_id).read_bytes()
        pages = service.document(data).pages
        if not 1 <= page <= len(pages):
            raise HTTPException(404, "page not found")
        return Response(pages[page - 1].image, media_type="image/png", headers={"Cache-Control": "max-age=86400"})

    @app.get("/api/documents/{doc_id}/words")
    def words(doc_id: str, page: int | None = None) -> list[dict[str, Any]]:
        with service.store.session() as s:
            d = get_doc(s, doc_id)
            return [w for w in d.words if page is None or w["page"] == page - 1]

    @app.patch("/api/documents/{doc_id}/fields/{field_id}", response_model=FieldOut)
    def patch_field(doc_id: str, field_id: int, body: FieldPatch) -> FieldOut:
        try:
            f = service.review(doc_id, field_id, value=body.value, word_ids=body.word_ids, approve=body.approve)
        except KeyError:
            raise HTTPException(404, "field not found") from None
        except ValueError as e:
            raise HTTPException(422, str(e)) from None
        return _field(f)

    @app.get("/api/documents/{doc_id}/export")
    def export(doc_id: str, format: Literal["json", "csv", "xlsx"] = "json") -> Response:
        fn, media = FORMATS[format]
        with service.store.session() as s:
            d = get_doc(s, doc_id)
            if d.status != "ready":
                raise HTTPException(409, f"document is {d.status}")
            body = fn(d)
            stem = Path(d.filename).stem or "document"
        return Response(
            body, media_type=media, headers={"Content-Disposition": f'attachment; filename="{stem}.{format}"'}
        )

    @app.get("/api/export")
    def export_many(
        ids: Annotated[str, Query(description="comma-separated document ids")],
        format: Literal["json", "csv", "xlsx"] = "xlsx",
    ) -> Response:
        fn, media = MANY_FORMATS[format]
        wanted = list(dict.fromkeys(i for i in ids.split(",") if i))
        if not wanted:
            raise HTTPException(422, "no documents given")
        with service.store.session() as s:
            docs = [get_doc(s, i) for i in wanted]
            if not_ready := [d.filename for d in docs if d.status != "ready"]:
                raise HTTPException(409, f"not ready yet: {', '.join(not_ready)}")
            body = fn(docs)
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M")
        name = f"citefield-{len(docs)}-documents-{stamp}.{format}"
        return Response(body, media_type=media, headers={"Content-Disposition": f'attachment; filename="{name}"'})

    @app.delete("/api/documents/{doc_id}", status_code=204)
    def delete(doc_id: str) -> None:
        with service.store.session() as s:
            s.delete(get_doc(s, doc_id))
        (data_dir / "uploads" / doc_id).unlink(missing_ok=True)

    web = resources.files("citefield").joinpath("web")
    if web.is_dir() and web.joinpath("index.html").is_file():
        root = Path(str(web))
        app.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

        public = {p.name for p in root.iterdir() if p.is_file() and p.name != "index.html"}  # favicon and such

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:
            return FileResponse(root / path if path in public else root / "index.html")

    return app
