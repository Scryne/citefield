"""REST API and the bundled review UI. v1 is single-user and binds to localhost by default: there is no login."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from importlib import resources
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import func, select

from citefield import __version__, providers
from citefield.export import FORMATS
from citefield.providers import Provider
from citefield.service import Service, Worker
from citefield.store.models import DocumentRow, FieldRow

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
    created_at: str


class DocumentOut(DocumentSummary):
    model: str | None
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


def _summary(d: DocumentRow) -> dict[str, Any]:
    return {
        "id": d.id,
        "filename": d.filename,
        "schema_name": d.schema_name,
        "status": d.status,
        "error": d.error,
        "to_review": sum(f.status == "review" for f in d.fields),
        "fields": len(d.fields),
        "created_at": d.created_at.isoformat(),
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

    @app.get("/api/schemas")
    def schemas() -> list[dict[str, Any]]:
        names = list(BUNDLED_SCHEMAS) + sorted(p.stem for p in (data_dir / "schemas").glob("*.json"))
        return [
            {"name": n, "description": sc.description, "fields": [f.name for f in sc.fields]}
            for n in names
            for sc in [service.schema(n)]
        ]

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
                "model": d.model,
                "pages": d.pages,
                "rules": d.rules,
                "possibly_missed": d.possibly_missed,
                "field_list": [_field(f) for f in d.fields],
            }

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

    @app.delete("/api/documents/{doc_id}", status_code=204)
    def delete(doc_id: str) -> None:
        with service.store.session() as s:
            s.delete(get_doc(s, doc_id))
        (data_dir / "uploads" / doc_id).unlink(missing_ok=True)

    web = resources.files("citefield").joinpath("web")
    if web.is_dir() and web.joinpath("index.html").is_file():
        root = Path(str(web))
        app.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:
            return FileResponse(root / "index.html")

    return app
