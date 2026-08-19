"""Stage 2: split a Docling-parsed document into retrieval chunks.

Strategy (header-aware primary, recursive fallback):
  1. Walk the document in reading order. Each SectionHeaderItem starts
     a new chunk; text under it accumulates into that chunk.
  2. TableItem is always its own chunk - never split, header row kept.
  3. If an accumulated section exceeds the token ceiling, recursively
     sub-split it (paragraph -> sentence -> word) and add overlap only
     on this fallback path, since only here is the cut point arbitrary.
  4. Every chunk carries metadata: source file, page number(s),
     section heading path, chunk index, content type.
"""

import re

from transformers import AutoTokenizer

TOKEN_CEILING = 512
RECURSIVE_OVERLAP_TOKENS = 75  # ~10-15% of 512, only used in fallback path

_tokenizer = AutoTokenizer.from_pretrained("bert-base-multilingual-cased")


def count_tokens(text: str) -> int:
    return len(_tokenizer.encode(text, add_special_tokens=False))


def _recursive_split(text: str, ceiling: int, overlap: int) -> list[dict]:
    """Fallback splitter for oversized sections. Tries paragraph breaks
    first, then sentences, then words - whichever keeps pieces under
    the ceiling. Applies overlap only here, since this is the one path
    where a cut point is a guess, not a real boundary.

    Returns a list of {"text": str, "overlap_text": str | None} - the
    overlap_text is the tail repeated from the previous piece, kept
    separate so callers/UI can highlight it instead of guessing."""
    if count_tokens(text) <= ceiling:
        return [{"text": text, "overlap_text": None}]

    for separator in ["\n\n", ". ", " "]:
        parts = [p for p in text.split(separator) if p.strip()]
        if len(parts) > 1:
            break
    else:
        parts = [text]

    pieces = []
    current = ""
    for part in parts:
        candidate = (current + separator + part) if current else part
        if count_tokens(candidate) <= ceiling:
            current = candidate
        else:
            if current:
                pieces.append(current)
            current = part
    if current:
        pieces.append(current)

    if len(pieces) <= 1:
        return [{"text": p, "overlap_text": None} for p in pieces]

    overlapped = [{"text": pieces[0], "overlap_text": None}]
    for piece in pieces[1:]:
        tail = _sentence_tail(overlapped[-1]["text"], overlap)
        overlapped.append({"text": tail + " " + piece, "overlap_text": tail})
    return overlapped


def _sentence_tail(text: str, max_tokens: int) -> str:
    """Returns whole trailing sentences from text, staying under
    max_tokens - never cuts a sentence in half. Falls back to the
    last sentence alone if even that exceeds the budget."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    tail_sentences = []
    token_total = 0
    for sentence in reversed(sentences):
        sentence_tokens = count_tokens(sentence)
        if tail_sentences and token_total + sentence_tokens > max_tokens:
            break
        tail_sentences.insert(0, sentence)
        token_total += sentence_tokens
    return " ".join(tail_sentences)


def chunk_document(doc, source_file: str) -> list[dict]:
    """Returns a list of chunk dicts, each with text + metadata."""
    chunks = []
    heading_stack = []  # [(level, text), ...]
    current_text_parts = []
    current_pages = set()
    chunk_index = 0

    def heading_path():
        return " > ".join(h[1] for h in heading_stack)

    def flush():
        nonlocal current_text_parts, current_pages, chunk_index
        if not current_text_parts:
            return
        section_text = "\n\n".join(current_text_parts)
        pieces = _recursive_split(section_text, TOKEN_CEILING, RECURSIVE_OVERLAP_TOKENS)
        for piece in pieces:
            chunk_index += 1
            chunks.append({
                "chunk_id": f"{source_file}_{chunk_index}",
                "chunk_index": chunk_index,
                "source_file": source_file,
                "page_number": sorted(current_pages) if current_pages else None,
                "section_heading": heading_path(),
                "content_type": "text",
                "token_count": count_tokens(piece["text"]),
                "text": piece["text"].strip(),
                "has_overlap": piece["overlap_text"] is not None,
                "overlap_text": piece["overlap_text"],
            })
        current_text_parts = []
        current_pages = set()

    for item, level in doc.iterate_items():
        label = getattr(item, "label", None)
        page_no = None
        if hasattr(item, "prov") and item.prov:
            page_no = item.prov[0].page_no

        if label == "section_header":
            flush()
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, item.text.strip()))
            continue

        if label == "table":
            flush()
            chunk_index += 1
            table_md = item.export_to_markdown(doc)
            chunks.append({
                "chunk_id": f"{source_file}_{chunk_index}",
                "chunk_index": chunk_index,
                "source_file": source_file,
                "page_number": [page_no] if page_no else None,
                "section_heading": heading_path(),
                "content_type": "table",
                "token_count": count_tokens(table_md),
                "text": table_md,
                "has_overlap": False,
                "overlap_text": None,
            })
            continue

        text = getattr(item, "text", "")
        if text and text.strip():
            current_text_parts.append(text.strip())
            if page_no:
                current_pages.add(page_no)

    flush()
    return chunks
