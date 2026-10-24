import io
from collections import Counter

from PIL import Image
from reportlab.pdfgen.canvas import Canvas

from citefield.eval.metrics import CENTER_MARGIN
from citefield.eval.synthpdf import make_pdf
from citefield.geometry import center_inside
from citefield.ingest import read_document
from citefield.ingest.reader import RawWord, _group_lines

VOCAB = ["Invoice", "No:", "INV-0042", "Total", "$1,234.50", "22-Apr-2018", "Due", "Date", "27AAAPL1234C1ZV", "Qty"]


class FakeOcr:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, png: bytes) -> list[RawWord]:
        self.calls += 1
        return [RawWord("TOTAL", (10, 50, 60, 70), 0.9), RawWord("45,500", (80, 52, 140, 71), 0.8)]


def _png(w: int, h: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "white").save(buf, format="PNG")
    return buf.getvalue()


def test_text_layer_words_match_what_was_drawn():
    pdf, gold = make_pdf(VOCAB, seed=3)
    ocr = FakeOcr()
    doc = read_document(pdf, ocr=ocr)
    assert ocr.calls == 0 and doc.pages[0].source == "pdf"
    assert Counter(w.text for w in doc.words) == Counter(g.text for g in gold)
    for g in gold:
        assert any(w.text == g.text and center_inside(w.box, g.box, CENTER_MARGIN) for w in doc.words), g
        # exact, not just overlapping: left, right and baseline-side edges agree. The top differs by convention only
        # (pdfplumber spans the full font size above the baseline, the generator uses the font's real ascent).
        assert any(
            w.text == g.text
            and abs(w.box[0] - g.box[0]) < 1
            and abs(w.box[2] - g.box[2]) < 1
            and abs(w.box[3] - g.box[3]) < 2
            for w in doc.words
        ), g


def test_measurement_is_not_trivially_true():
    """Shifting the gold boxes by a line height must break the location check used above."""
    pdf, gold = make_pdf(VOCAB, seed=3)
    words = read_document(pdf, ocr=FakeOcr()).words
    shifted = [(g.text, (g.box[0], g.box[1] + 40, g.box[2], g.box[3] + 40)) for g in gold]
    located = sum(any(w.text == t and center_inside(w.box, b, CENTER_MARGIN) for w in words) for t, b in shifted)
    assert located < len(gold) / 2


def test_force_ocr_and_scanned_pdf_use_ocr():
    pdf, _ = make_pdf(VOCAB, seed=1)
    ocr = FakeOcr()
    assert read_document(pdf, ocr=ocr, force_ocr=True).pages[0].source == "ocr" and ocr.calls == 1

    buf = io.BytesIO()
    Image.new("RGB", (600, 800), "white").save(buf, format="PDF")  # image only, no text layer
    doc = read_document(buf.getvalue(), ocr=ocr)
    assert doc.pages[0].source == "ocr" and ocr.calls == 2 and [w.text for w in doc.words] == ["TOTAL", "45,500"]


def test_image_exif_rotation_is_applied():
    im = Image.new("RGB", (300, 100), "white")
    exif = im.getexif()
    exif[0x0112] = 6  # rotate 90 degrees on display
    buf = io.BytesIO()
    im.save(buf, format="JPEG", exif=exif)
    page = read_document(buf.getvalue(), ocr=FakeOcr()).pages[0]
    assert (page.width, page.height) == (100, 300)


def test_ids_and_lines_run_across_pages_in_reading_order():
    buf = io.BytesIO()
    c = Canvas(buf)
    c.drawString(100, 700, "first line here")
    c.drawString(100, 600, "second")
    c.showPage()
    c.drawString(100, 700, "third page line")
    c.save()
    words = read_document(buf.getvalue(), ocr=FakeOcr()).words
    assert [w.id for w in words] == list(range(len(words)))
    assert [w.text for w in words] == ["first", "line", "here", "second", "third", "page", "line"]
    assert [w.line for w in words] == [0, 0, 0, 1, 2, 2, 2]
    assert [w.page for w in words] == [0, 0, 0, 0, 1, 1, 1]


def test_group_lines_joins_a_printed_row_and_splits_rows():
    # item name and price detected separately, slightly offset and of different height: one printed row
    boxes = [(10, 100, 120, 118), (300, 103, 360, 119), (10, 140, 80, 158)]
    assert _group_lines(boxes) == [0, 0, 1]


def test_real_ocr_reads_a_rendered_page():
    pdf, gold = make_pdf(VOCAB, seed=5)
    doc = read_document(pdf, force_ocr=True)
    found = sum(any(w.text == g.text for w in doc.words) for g in gold)
    assert found / len(gold) > 0.9


def test_words_within_a_line_are_ordered_left_to_right():
    class Reversed(FakeOcr):
        def __call__(self, png: bytes) -> list[RawWord]:
            return [RawWord("45,500", (80, 52, 140, 71)), RawWord("TOTAL", (10, 50, 60, 70))]

    assert [w.text for w in read_document(_png(200, 100), ocr=Reversed()).words] == ["TOTAL", "45,500"]


def test_rotated_pdf_page_goes_to_ocr():
    buf = io.BytesIO()
    c = Canvas(buf)
    c.setPageRotation(90)
    c.drawString(100, 700, "rotated page text here")
    c.save()
    ocr = FakeOcr()
    assert read_document(buf.getvalue(), ocr=ocr).pages[0].source == "ocr" and ocr.calls == 1


def test_cache_returns_the_same_document_without_reading_again(tmp_path):
    from citefield.ingest.cache import read_cached

    pdf, _ = make_pdf(VOCAB, seed=2)
    ocr = FakeOcr()
    first = read_cached(pdf, tmp_path, ocr=ocr, force_ocr=True)
    second = read_cached(pdf, tmp_path, ocr=ocr, force_ocr=True)
    assert ocr.calls == 1
    assert second.words == first.words and second.pages[0].image == first.pages[0].image
    assert read_cached(pdf, tmp_path, ocr=ocr).pages[0].source == "pdf"  # forced OCR is cached separately
