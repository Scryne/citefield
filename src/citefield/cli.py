"""Command line: extract one document, serve the API and review UI, or run an evaluation."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from citefield import __version__


def _data_dir(arg: str | None) -> Path:
    return Path(arg or os.environ.get("CITEFIELD_DATA") or Path.home() / ".citefield")


def cmd_extract(a: argparse.Namespace) -> int:
    from citefield import providers
    from citefield.extract import extract
    from citefield.ingest.cache import read_cached
    from citefield.schema import load
    from citefield.verify import verify

    data = Path(a.file).read_bytes()
    doc = read_cached(data, _data_dir(a.data) / "ingest")
    schema = load(a.schema)
    ex = extract(doc, schema, providers.get(a.provider, a.model))
    verdict = verify(ex, schema)
    out = [
        {
            "field": f.field,
            "value": f.value,
            "item": f.item,
            "status": d.status,
            "reasons": d.reasons,
            "page": None if f.page is None else f.page + 1,
            "box": f.box,
        }
        for f, d in zip(ex.fields, verdict.decisions, strict=True)
    ]
    json.dump({"fields": out, "rules": [r.__dict__ for r in verdict.rules]}, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


def cmd_serve(a: argparse.Namespace) -> int:
    import uvicorn

    from citefield.api import create_app

    os.environ.setdefault("CITEFIELD_PROVIDER", a.provider)
    if a.model:
        os.environ["CITEFIELD_MODEL"] = a.model
    uvicorn.run(create_app(_data_dir(a.data)), host=a.host, port=a.port)
    return 0


def cmd_eval(a: argparse.Namespace) -> int:
    from citefield.eval.run import main as run

    run(a.rest)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="citefield", description="Document field extraction with cited sources.")
    p.add_argument("--version", action="version", version=f"citefield {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    e = sub.add_parser("extract", help="extract fields from one document and print JSON")
    e.add_argument("file")
    e.add_argument("--schema", default="invoice", help="bundled template (invoice, receipt) or a JSON schema file")
    e.add_argument("--provider", default="anthropic", help="anthropic, openai, ollama, claude-code")
    e.add_argument("--model")
    e.add_argument("--data", help="data directory (default ~/.citefield)")
    e.set_defaults(fn=cmd_extract)

    s = sub.add_parser("serve", help="run the API and the review UI")
    s.add_argument("--host", default="127.0.0.1", help="v1 has no login: keep it on localhost unless you add one")
    s.add_argument("--port", type=int, default=8484)
    s.add_argument("--provider", default="anthropic")
    s.add_argument("--model")
    s.add_argument("--data")
    s.set_defaults(fn=cmd_serve)

    v = sub.add_parser("eval", help="evaluate on a labelled dataset (see citefield.eval.run)")
    v.add_argument("rest", nargs=argparse.REMAINDER)
    v.set_defaults(fn=cmd_eval)

    a = p.parse_args(argv)
    return int(a.fn(a))
