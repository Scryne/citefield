"""Born-digital PDFs whose word positions are known exactly, for measuring the text-layer path against OCR.
No open invoice dataset ships PDFs with word boxes (FATURA's boxes are per block), so the layout is generated: words
are drawn one by one, and each gold box comes from the font metrics used to draw it.
Needs reportlab (dev dependency)."""

from __future__ import annotations

import io
import random
from collections.abc import Sequence
from dataclasses import dataclass

from citefield.geometry import Box

FONTS = ("Helvetica", "Times-Roman", "Courier", "Helvetica-Bold")
A4 = (595.0, 842.0)


@dataclass(frozen=True)
class SynthWord:
    text: str
    box: Box  # pixels at `scale`, origin top-left


def make_pdf(vocab: Sequence[str], seed: int, scale: float = 2.0) -> tuple[bytes, list[SynthWord]]:
    from reportlab.pdfbase.pdfmetrics import getAscentDescent, stringWidth
    from reportlab.pdfgen.canvas import Canvas

    rng = random.Random(seed)
    w, h = A4
    buf = io.BytesIO()
    c = Canvas(buf, pagesize=A4)
    gold: list[SynthWord] = []
    y = h - 50
    while y > 60:
        font, size = rng.choice(FONTS), rng.choice((7, 8, 9, 10, 11, 12, 14))
        ascent, descent = getAscentDescent(font, size)
        x = rng.uniform(40, 120)
        for _ in range(rng.randint(1, 3)):  # columns on one row, each a run of words drawn as one string
            run = [rng.choice(vocab) for _ in range(rng.randint(1, 4))]
            text = " ".join(run)
            if x + stringWidth(text, font, size) > w - 40:
                break
            c.setFont(font, size)
            c.drawString(x, y, text)
            cursor = x
            for word in run:
                width = stringWidth(word, font, size)
                box = (cursor * scale, (h - y - ascent) * scale, (cursor + width) * scale, (h - y - descent) * scale)
                gold.append(SynthWord(word, box))
                cursor += width + stringWidth(" ", font, size)
            x = cursor + rng.uniform(20, 80)
        y -= size * rng.uniform(1.3, 2.4)
    c.save()
    return buf.getvalue(), gold
