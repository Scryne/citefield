"""Documents in, page images and words with ids out."""

from citefield.ingest.models import Document, Page, Word
from citefield.ingest.reader import read_document

__all__ = ["Document", "Page", "Word", "read_document"]
