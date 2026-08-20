"""Stage 1 (alternate path): parse a PDF straight to structured Markdown
using Docling's layout model - headings, tables, and reading order are
detected from the PDF's actual layout, not guessed by an LLM from flat text.
"""

from docling.document_converter import DocumentConverter
from docling_core.types.doc.document import DoclingDocument

_converter = DocumentConverter()


def parse_document(pdf_path: str) -> DoclingDocument:
    """Returns Docling's structured document - used by the chunker to read
    per-element page numbers, heading levels, and table boundaries."""
    result = _converter.convert(pdf_path)
    return result.document


def parse_to_markdown(pdf_path: str) -> str:
    return parse_document(pdf_path).export_to_markdown()
