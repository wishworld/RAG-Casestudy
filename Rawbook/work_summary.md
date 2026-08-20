# Work Summary - Stage 1 (PDF to Markdown)

> **Conversion note:** Render with `pandoc --wrap=preserve` plus a
> monospace reference template. Default converters may reflow the
> ASCII diagrams below.

## Goal

Local, privacy-first, NotebookLM-style enterprise knowledge assistant
(RAG system). Build strategy: one pipeline stage at a time - build,
test on a real document, fix if broken, then move to the next stage.

---

## 1. Local LLM setup (discovered, already in place)

Ollama + qwen2.5:7b, fully offline, OpenAI-compatible API at
`localhost:11434`. Full details in
[QWEN_Local_LLM_setupDetails.md](QWEN_Local_LLM_setupDetails.md).

---

## 2. Stage 1 v1: PyMuPDF + LLM

```text
PDF file
   |
   v
PyMuPDF (extract raw text, page by page)
   |
   v
qwen2.5:7b via Ollama (clean + restructure into MD)
   |
   v
.md file
```

Built as a real app, not a throwaway script:

```text
app/
  backend/
    main.py          - FastAPI, /convert endpoint
    pdf_parser.py     - PyMuPDF text extraction
    llm_cleanup.py    - Ollama qwen2.5:7b call
  frontend/
    index.html        - upload + raw/MD side-by-side viewer
  venv/                - isolated Python 3.12 environment
  uploads/, outputs/   - runtime artifacts
```

---

## 3. Test run and bugs found

Tested on a real 5-page PDF (SpiceMoney Travel Claim FAQ,
bilingual English/Hindi, contains a table).

```text
BUG 1: Table split
  1 real table (Topic | DSM | BSM) -> became 5 broken 2-column
  tables with the header orphaned from its data

BUG 2: Numbering drift
  "Q9" appeared twice in the output with DIFFERENT content -
  the model lost track of where the document's numbering was
```

---

## 4. Root cause

```text
CODE (main.py) looped once per PDF page:

  for page_text in pages:
      md_pages.append(clean_to_markdown(page_text))

Each LLM call was BLIND to every other call - page 2 had no
idea what page 1 had already written (no shared Q-number state,
no idea a table was still open).

NOT a context-size problem - each page was small and fit easily
within the 4096-token window. It was a design choice (1 call per
page, no shared memory) that caused the drift.
```

---

## 5. Research: best practices for PDF -> MD for RAG

Key findings from web search:

- Parsing quality is the ceiling for the whole pipeline - "if the
  parser flattens everything to a character stream, no chunking
  strategy downstream can recover what was lost."
- Layout-aware parsers (Docling, Marker) beat LLM-guessed structure
  for table-heavy or multi-column documents.
- Attach metadata (filename, page number, section) during parsing,
  not after chunking - much harder to reconstruct later.
- Chunking default: ~512 tokens, layout-aware (split on headings/
  table boundaries, not blind fixed-size cuts). Overlap (10-20%)
  is a common hedge but 2026 research shows mixed evidence of benefit.

---

## 6. Stage 1 v2: added Docling as an alternate pipeline

```text
PDF file
   |
   v
Docling (layout model detects headings, tables, reading order
directly from the PDF's structure - no LLM guessing involved)
   |
   v
.md file
```

Also fixed along the way: Ollama's OpenAI-compatible endpoint was
silently ignoring the `num_ctx` option (context stayed at 4096
regardless of what was requested). Switched `llm_cleanup.py` to
Ollama's native `/api/chat` endpoint, confirmed context now
correctly raised to 16384 via `ollama ps`.

New file: `app/backend/docling_parser.py`.
`main.py` now takes `?method=pymupdf_llm|docling` so both pipelines
run through the same `/convert` endpoint.
`index.html` got a dropdown to pick which pipeline to run.

---

## 7. Re-test result

Same PDF, same two bugs checked:

```text
BUG 1 (table split):     FIXED - single correct 5-row x 3-column table
BUG 2 (numbering drift): FIXED - "Q9" appears twice correctly
                          (English + Hindi translation of the SAME
                          question, not a numbering error)
BONUS: no hallucinated headings (v1 had invented two section
       titles not present in the source document)
```

New minor issue introduced by Docling itself: occasional stray
spaces inside Devanagari (Hindi) conjuncts from its OCR pass -
much smaller problem than the two structural bugs it fixed.

Timing: first Docling run took ~4 minutes (one-time OCR model
download). Second run on the same doc: 18.4 seconds.

---

## 8. Status

Stage 1 (PDF -> Markdown) verified working. Docling is the clear
winner on structure fidelity for this document type and is wired
into the GUI as a selectable pipeline alongside the original
PyMuPDF+LLM path for continued comparison.

**Not yet started:** Stage 2 (Chunking).
