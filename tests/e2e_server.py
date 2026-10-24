"""Server for the UI end-to-end test: the real app on a fresh data directory, one receipt already processed, and a
fake model whose image-only read disagrees on the total, so the review queue has work in it.

Usage: python tests/e2e_server.py <port>
"""

import sys
import tempfile
from pathlib import Path

import uvicorn

sys.path.insert(0, str(Path(__file__).parent))
from test_api import FakeProvider, receipt_pdf  # noqa: E402

from citefield.api import create_app  # noqa: E402


def main() -> None:
    data = Path(tempfile.mkdtemp(prefix="citefield-e2e-"))
    app = create_app(data, lambda: FakeProvider(second_total="7.80"), worker=True)
    service = app.state.service
    doc_id = service.submit("coffee-receipt.pdf", receipt_pdf(), "receipt")
    service.claim_next()
    service.process(doc_id)
    (data / "e2e-doc-id").write_text(doc_id)
    print(f"E2E_DOC {doc_id}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=int(sys.argv[1]), log_level="warning")


if __name__ == "__main__":
    main()
