"""End-to-end evaluation on a labelled dataset: ingest, both reads, evidence, then value and location accuracy.

Reads are cached by (provider, model, prompt, images), so re-scoring after a change to evidence rules costs nothing.

Usage: python -m citefield.eval.run <cord|fatura> <n> <provider> [model] [--data DIR] [--no-second] [--workers N]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Any

from citefield import providers
from citefield.eval import datasets
from citefield.eval.metrics import Pred, Summary, match, summarize
from citefield.extract import Extracted, extract, primary_prompt, secondary_prompt
from citefield.ingest.cache import read_cached
from citefield.providers import Provider, ReadResult
from citefield.schema import load
from citefield.verify import verify


class CachedProvider:
    def __init__(self, inner: Provider, directory: Path) -> None:
        self.inner, self.dir = inner, directory
        self.name, self.model = inner.name, inner.model
        directory.mkdir(parents=True, exist_ok=True)

    def read(self, prompt: str, images: list[bytes], json_schema: dict[str, Any] | None = None) -> ReadResult:
        h = hashlib.sha256()
        texts = (self.name, self.model, prompt, json.dumps(json_schema, sort_keys=True))
        for part in [t.encode("utf-8") for t in texts] + images:
            h.update(part)
            h.update(b"\0")
        path = self.dir / f"{h.hexdigest()}.json"
        if path.exists():
            return ReadResult(**json.loads(path.read_text("utf-8")))
        r = self.inner.read(prompt, images, json_schema)
        path.write_text(json.dumps(asdict(r), ensure_ascii=False), "utf-8")
        return r


# $ per million tokens (input, output), platform.claude.com, 2026-10-24
API_PRICES = {"claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50)}


def image_tokens(width: int, height: int, long_side: int = 2576, cap: int = 4784) -> int:
    """Claude vision token formula: ceil(w/28) * ceil(h/28) after downscaling to the long-side limit."""
    scale = min(1.0, long_side / max(width, height))
    w, h = int(width * scale), int(height * scale)
    return min(cap, -(-w // 28) * -(-h // 28))


def api_estimate(images: list[tuple[int, int]], prompt_chars: int, output_tokens: int) -> dict[str, float]:
    """What the same reads would cost on the API. claude-code reports its own figure, which includes the CLI context."""
    tin = sum(image_tokens(w, h) for w, h in images) + prompt_chars // 4
    return {m: (tin * p[0] + output_tokens * p[1]) / 1e6 for m, p in API_PRICES.items()}


def _preds(fields: list[Extracted]) -> list[Pred]:
    return [Pred(f.field, f.value, f.box) for f in fields]


TRIGGERS = (  # reason text -> trigger, most specific first
    ("is also cited as", "collision"),
    ("second read", "second_read"),
    ("confidence", "confidence"),
    ("does not hold", "rule"),
    ("check digit", "rule"),
    ("cited", "citation"),
)


def trigger(reason: str) -> str:
    return next(t for key, t in TRIGGERS if key in reason)


def main(argv: list[str] | None = None) -> dict[str, Any]:
    ap = argparse.ArgumentParser(prog="citefield-eval")
    ap.add_argument("dataset", choices=["cord", "fatura"])
    ap.add_argument("n", type=int)
    ap.add_argument("--start", type=int, default=0, help="skip the first documents (held-out slices)")
    ap.add_argument("provider")
    ap.add_argument("model", nargs="?")
    ap.add_argument("--data", type=Path, default=Path(".veri"))
    ap.add_argument("--no-second", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)

    schema = load(a.dataset)
    items = list(datasets.cord(a.data, a.n, a.start) if a.dataset == "cord" else datasets.fatura(a.data, a.n, a.start))
    # FATURA label boxes include the caption ("Total: 1,234"), so values match by containment, as text (S1)
    kind_of = schema.kind_of if a.dataset == "cord" else (lambda _: "text")
    containment = a.dataset == "fatura"
    provider = CachedProvider(providers.get(a.provider, a.model), a.data / "cache" / "reads")

    def one(item: datasets.Item) -> dict[str, Any]:
        doc = read_cached(item.image, a.data / "cache" / "ingest")
        ex = extract(doc, schema, provider, second=not a.no_second)
        preds = _preds(ex.fields)
        matched = match(item.gold, preds, kind_of, containment=containment)
        right = {id(m.pred) for m in matched if m.pred is not None}
        verdict = verify(ex, schema)
        decided = [
            {
                "field": f.field,
                "value": f.value,
                "correct": id(p) in right,
                "status": d.status,
                "triggers": sorted({trigger(r) for r in d.reasons}),
            }
            for f, p, d in zip(ex.fields, preds, verdict.decisions, strict=True)
        ]
        return {
            "decided": decided,
            "id": item.id,
            "matches": matched,
            "citation": Counter(f.citation for f in ex.fields),
            "dropped": ex.dropped,
            "second": len(ex.second),
            "reads": ex.reads,
            "api": api_estimate(
                [(p.width, p.height) for p in doc.pages] * len(ex.reads),
                len(primary_prompt(schema, doc)) + (0 if a.no_second else len(secondary_prompt(schema))),
                sum(rd.output_tokens for rd in ex.reads),
            ),
        }

    with ThreadPoolExecutor(a.workers) as pool:
        results = list(pool.map(one, items))

    def total(key: str) -> Summary:
        return summarize([m for r in results for m in r[key]])

    reads = [rd for r in results for rd in r["reads"]]
    decided = [dict(d, id=r["id"]) for r in results for d in r["decided"]]
    wrong = [d for d in decided if not d["correct"]]
    fired: dict[str, dict[str, int]] = {}
    for d in decided:
        for t in d["triggers"]:
            fired.setdefault(t, {"on_wrong": 0, "on_correct": 0})["on_wrong" if not d["correct"] else "on_correct"] += 1
    costs = [rd.cost_usd for rd in reads if rd.cost_usd is not None]
    report = {
        "dataset": a.dataset,
        "documents": len(items),
        "slice": [a.start, a.start + a.n - 1],
        "provider": a.provider,
        "model": provider.model,
        "second_read": not a.no_second,
        "accuracy": asdict(total("matches")),
        "citation": dict(sum((r["citation"] for r in results), Counter())),
        "dropped_by_type_gate": sum(r["dropped"] for r in results),
        "review": {
            "predictions": len(decided),
            "wrong": len(wrong),
            "wrong_sent_to_review": sum(d["status"] == "review" for d in wrong),
            "auto_share": round(sum(d["status"] == "auto" for d in decided) / max(len(decided), 1), 3),
            "auto_error_rate": round(
                sum(d["status"] == "auto" for d in wrong) / max(sum(d["status"] == "auto" for d in decided), 1), 3
            ),
            "triggers": fired,
            "wrong_auto_approved": [
                {k: d[k] for k in ("id", "field", "value")} for d in wrong if d["status"] == "auto"
            ],
        },
        "per_document": {
            "input_tokens": round(sum(rd.input_tokens for rd in reads) / len(items)),
            "output_tokens": round(sum(rd.output_tokens for rd in reads) / len(items)),
            "cost_usd_reported": round(sum(costs) / len(items), 4) if costs else None,
            "seconds_per_read": round(sum(rd.seconds for rd in reads) / max(len(reads), 1), 1),
            "api_estimate_usd": {m: round(sum(r["api"][m] for r in results) / len(items), 5) for m in API_PRICES},
        },
    }
    span = f"{a.start}-{a.start + a.n - 1}" if a.start else str(a.n)
    out = (
        a.data / "reports" / f"{a.dataset}-{span}-{a.provider}-{provider.model}{'-single' if a.no_second else ''}.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1), "utf-8")
    print(json.dumps(report, indent=1))
    return report


if __name__ == "__main__":
    main()
