"""Database tables. SQLite in v1 (single user, self-hosted); the same models move to Postgres for the hosted v2."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class DocumentRow(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    schema_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)  # queued|processing|ready|failed
    error: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(String(50))
    model: Mapped[str | None] = mapped_column(String(100))
    pages: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)  # index, width, height, source
    words: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    rules: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    possibly_missed: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    usage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # tokens, cost, seconds per read
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)

    fields: Mapped[list[FieldRow]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="FieldRow.position"
    )


class FieldRow(Base):
    __tablename__ = "fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(100))
    value: Mapped[str] = mapped_column(Text)
    item: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float | None]
    evidence: Mapped[list[int]] = mapped_column(JSON, default=list)
    citation: Mapped[str] = mapped_column(String(20))
    box: Mapped[list[float] | None] = mapped_column(JSON)
    page: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))  # auto|review|approved|corrected
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    extracted_value: Mapped[str] = mapped_column(Text)  # as read, kept when a reviewer corrects the value
    reviewed_at: Mapped[datetime | None]

    document: Mapped[DocumentRow] = relationship(back_populates="fields")
