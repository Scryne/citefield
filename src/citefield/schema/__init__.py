"""Extraction schemas: typed, described fields (K-Şema, S3). JSON on disk so users can write their own."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Literal, cast

Kind = Literal["text", "amount", "count", "date", "id"]
KINDS: tuple[str, ...] = ("text", "amount", "count", "date", "id")


@dataclass(frozen=True)
class FieldSpec:
    name: str
    kind: Kind
    description: str = ""
    group: str | None = None  # repeated group such as line items; members carry an item number
    anchor: bool = False  # the group field that starts an item (its name); K-Satır measures rows from it


@dataclass(frozen=True)
class Schema:
    name: str
    description: str
    fields: tuple[FieldSpec, ...]

    def field(self, name: str) -> FieldSpec | None:
        return next((f for f in self.fields if f.name == name), None)

    def kind_of(self, name: str) -> Kind:
        f = self.field(name)
        return f.kind if f else "text"


def parse(data: dict[str, Any]) -> Schema:
    raw_fields = data.get("fields")
    if not isinstance(raw_fields, list) or not raw_fields:
        raise ValueError("schema needs a non-empty 'fields' list")
    fields = []
    for f in raw_fields:
        kind = f.get("kind", "text")
        if kind not in KINDS:
            raise ValueError(f"field {f.get('name')!r}: kind must be one of {', '.join(KINDS)}")
        fields.append(
            FieldSpec(f["name"], cast(Kind, kind), f.get("description", ""), f.get("group"), bool(f.get("anchor")))
        )
    names = [f.name for f in fields]
    if len(set(names)) != len(names):
        raise ValueError("field names must be unique")
    for g in {f.group for f in fields if f.group}:
        if sum(f.anchor for f in fields if f.group == g) != 1:
            raise ValueError(f"group {g!r} needs exactly one anchor field")
    return Schema(str(data.get("name", "custom")), str(data.get("description", "")), tuple(fields))


def load(name_or_path: str) -> Schema:
    """A bundled template by name (`invoice`, `receipt`, and the evaluation schemas) or a JSON file path."""
    p = Path(name_or_path)
    if p.suffix == ".json" and p.exists():
        return parse(json.loads(p.read_text("utf-8")))
    text = resources.files("citefield.schema").joinpath(f"templates/{name_or_path}.json").read_text("utf-8")
    return parse(json.loads(text))
