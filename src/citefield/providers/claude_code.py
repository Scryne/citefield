"""`claude -p` on the developer's own Claude Code login. Development and evaluation only: the spikes were measured this
way, so the published numbers can be reproduced without an API key.

The CLI reads images through its Read tool, so pages are written to a temporary folder that is the only extra
directory the call may read. It runs from an empty working directory so no project instructions leak into the prompt.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from citefield.providers import ReadResult


class ClaudeCodeProvider:
    name = "claude-code"

    def __init__(self, model: str = "sonnet", timeout: float = 600) -> None:
        exe = shutil.which("claude")
        if exe is None:
            raise RuntimeError("the claude-code provider needs the `claude` CLI on PATH")
        self.exe, self.model, self.timeout = exe, model, timeout

    def read(self, prompt: str, images: list[bytes], json_schema: dict[str, Any] | None = None) -> ReadResult:
        with tempfile.TemporaryDirectory(prefix="citefield-") as tmp:
            pages = Path(tmp) / "pages"
            work = Path(tmp) / "work"
            pages.mkdir()
            work.mkdir()
            paths = []
            for i, png in enumerate(images):
                p = pages / f"page-{i + 1}.png"
                p.write_bytes(png)
                paths.append(p.as_posix())
            if paths:
                listing = "\n".join(f"- page {i + 1}: {p}" for i, p in enumerate(paths))
                prompt = f"Read each page image of the document with the Read tool:\n{listing}\n\n{prompt}"
            cmd = [self.exe, "-p", "--model", self.model, "--output-format", "json"]
            cmd += ["--allowedTools", "Read", "--add-dir", str(pages)] if paths else ["--tools", ""]
            env = dict(os.environ, PROJE_SISTEMI_INVOKED_BY="citefield", PYTHONUTF8="1")
            t0 = time.perf_counter()
            # bytes in and out: on Windows the child's text encoding is the ANSI code page, not UTF-8
            r = subprocess.run(
                cmd, input=prompt.encode("utf-8"), capture_output=True, cwd=work, env=env, timeout=self.timeout
            )
            seconds = time.perf_counter() - t0
        if r.returncode != 0:
            raise RuntimeError(f"claude -p failed: {r.stderr.decode('utf-8', 'replace')[-500:]}")
        out = json.loads(r.stdout.decode("utf-8"))
        usage = out.get("usage") or {}
        tokens_in = sum(
            int(usage.get(k) or 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
        )
        return ReadResult(
            str(out.get("result", "")),
            self.model,
            tokens_in,
            int(usage.get("output_tokens") or 0),
            out.get("total_cost_usd"),
            seconds,
        )
