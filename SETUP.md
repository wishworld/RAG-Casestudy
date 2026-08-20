# RAG Case Study - Setup Guide

Local, privacy-first RAG (Retrieval-Augmented Generation) pipeline: PDF
upload through LLM-generated, cited answers, entirely on-machine (no
external API calls, no cloud LLM). Every pipeline stage is exposed as
an independently-triggerable step in the GUI - built for learning RAG
internals, not just using a framework.

This doc is written so a fresh Claude Code session (or a human) can set
this up from zero with no prior context. Follow it top to bottom -
later steps depend on earlier ones.

## What you're building

```text
+-----------+   +---------+   +---------+   +----------+
| PostgreSQL| + | pgvector| + | Ollama  | + | FastAPI  |
| 17        |   | ext.    |   | (local  |   | backend  |
| (storage) |   |         |   | LLM)    |   | + GUI    |
+-----------+   +---------+   +---------+   +----------+
      \              |              |             /
       \_____________|______________|____________/
                      |
              http://localhost:8000
           (single-page app, no build step)
```

Stages implemented: PDF->Markdown (Docling) -> Chunk -> Embed (bge-m3)
-> Store (pgvector) -> Semantic Search -> Keyword Search (Postgres FTS)
-> RRF Hybrid Fusion -> No-Answer Detection -> Context Construction ->
LLM Answer Generation (qwen2.5:7b) -> Batch Evaluation harness.

---

## 1. Prerequisites

| Tool | Version used | Check | Install if missing |
|---|---|---|---|
| macOS | Darwin (arm64 tested) | `uname -a` | - |
| Xcode Command Line Tools | any recent (Homebrew needs this) | `xcode-select -p` | `xcode-select --install` |
| Homebrew | any recent | `brew --version` | see https://brew.sh |
| Python | 3.12.x | `python3 --version` | `brew install python@3.12` |
| PostgreSQL | 17.x | `psql --version` | `brew install postgresql@17` (step 2) |
| pgvector | 0.8.x (Postgres extension, not a Python package) | `psql -d rag_casestudy -c "SELECT extversion FROM pg_extension WHERE extname='vector';"` | `brew install pgvector` (step 2) |
| Ollama | any recent (0.32.x tested) | `ollama --version` | `brew install ollama` or https://ollama.com (step 3) |

Disk space - budget ~8GB free, broken down:

| What | Size | Downloaded by |
|---|---|---|
| Python packages (`pip install -r requirements.txt`) | ~1.4GB | pip, step 4 - torch + docling's bundled models are the bulk of this |
| Docling's own layout-detection model weights | a few hundred MB | automatic, first PDF conversion, step 4 |
| HuggingFace tokenizer files (`bert-base-multilingual-cased`) | ~1GB | automatic, first backend import, step 4 - cached under `~/.cache/huggingface/` |
| Ollama model: `bge-m3` (embeddings) | ~1.2GB | `ollama pull bge-m3`, step 3 |
| Ollama model: `qwen2.5:7b` (answers) | ~4.7GB | `ollama pull qwen2.5:7b`, step 3 |

---

## 2. PostgreSQL + pgvector

```bash
brew install postgresql@17
brew services start postgresql@17

# pgvector extension
brew install pgvector

# Create the database (uses your OS user as the Postgres role - no
# password is set anywhere in this project; DB_URL in vectorstore.py
# is postgresql://localhost/rag_casestudy with no credentials)
createdb rag_casestudy
```

Verify:
```bash
pg_isready -h localhost
psql -d rag_casestudy -c "SELECT 1;"
```

### 2a. Enable the extension and create the schema

Run this exact block - it is the live schema pulled from the working
database, not a reconstruction:

```bash
psql -d rag_casestudy <<'EOF'
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id           SERIAL PRIMARY KEY,
    job_id       TEXT NOT NULL UNIQUE,
    filename     TEXT NOT NULL,
    uploaded_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id               SERIAL PRIMARY KEY,
    chunk_id         TEXT NOT NULL UNIQUE,
    document_id      INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index      INTEGER NOT NULL,
    source_file      TEXT NOT NULL,
    page_number      INTEGER[],
    section_heading  TEXT,
    content_type     TEXT NOT NULL,
    token_count      INTEGER NOT NULL,
    text             TEXT NOT NULL,
    has_overlap      BOOLEAN NOT NULL DEFAULT false,
    overlap_text     TEXT,
    embedding        vector(1024),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    search_vector    tsvector
);

CREATE INDEX IF NOT EXISTS chunks_document_id_idx ON chunks (document_id);

-- HNSW index for fast approximate cosine-similarity search (Stage 5/7)
CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);

-- Full-text search support (Stage 8) - trigger keeps search_vector in
-- sync automatically on every insert/update of chunks.text
CREATE OR REPLACE FUNCTION chunks_search_vector_update() RETURNS trigger AS $$
BEGIN
  NEW.search_vector := to_tsvector('english', coalesce(NEW.text, ''));
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS chunks_search_vector_trigger ON chunks;
CREATE TRIGGER chunks_search_vector_trigger
    BEFORE INSERT OR UPDATE OF text ON chunks
    FOR EACH ROW EXECUTE FUNCTION chunks_search_vector_update();

CREATE INDEX IF NOT EXISTS chunks_search_vector_idx ON chunks USING gin (search_vector);
EOF
```

Verify:
```bash
psql -d rag_casestudy -c "\dt"
# expect: documents, chunks

psql -d rag_casestudy -c "SELECT extname, extversion FROM pg_extension WHERE extname='vector';"
# expect: vector | 0.8.x (any 0.5+ works - pgvector.psycopg only needs the Python client >=0.5)
```

---

## 3. Ollama + models

```bash
open -a Ollama   # or: ollama serve (if installed via brew, not the .app)
```

Verify it's up:
```bash
curl -s -m 3 http://localhost:11434/api/tags
```

Pull the two models this app calls by name (hardcoded in
`embedder.py` and `answer_generator.py` - do not substitute other
model names without editing those files):

```bash
ollama pull bge-m3        # embedding model, 1024-dim, ~1.2GB
ollama pull qwen2.5:7b    # answer-generation LLM, ~4.7GB
```

Verify:
```bash
ollama list
# expect both bge-m3 and qwen2.5:7b listed
```

**Note on the Ollama API:** `answer_generator.py` deliberately uses
Ollama's *native* `/api/chat` endpoint, not the OpenAI-compatible
`/v1/chat/completions` endpoint - the native endpoint is the only one
that reliably honors `options.num_ctx`. Don't "fix" this to use the
OpenAI-compatible path without re-verifying context-window behavior.

---

## 4. Python backend

```bash
cd app
python3 -m venv venv
source venv/bin/activate      # zsh/bash; use venv/bin/activate.fish for fish
pip install --upgrade pip
pip install -r backend/requirements.txt
```

This installs ~115 packages transitively (torch + docling's own model
weights are the bulk of it) - expect several minutes and ~1.4GB on
disk.

First run of `docling` will also lazy-download its own layout-detection
model weights on first PDF conversion (separate from the pip install) -
this happens automatically the first time you hit Convert in the GUI,
requires network access once, and is cached afterward.

`transformers`' `AutoTokenizer.from_pretrained("bert-base-multilingual-cased")`
(used only for local token counting in `chunker.py` - not an LLM call)
similarly downloads its tokenizer files on first import and caches them
under `~/.cache/huggingface/`.

---

## 5. Run the backend

```bash
cd app/backend
source ../venv/bin/activate   # if not already active
uvicorn main:app --reload --port 8000
```

Verify:
```bash
curl -s -m 3 http://localhost:8000/documents
# expect: {"documents": []}   (empty list on a fresh DB)
```

Open the app:
```
http://localhost:8000
```

---

## 6. First end-to-end test

Use this exact sequence to confirm every layer works, not just that
the server started:

1. **Input tab** - upload any PDF, click **Convert** (tests Docling).
2. Click **Chunk** (tests the chunker + local tokenizer).
3. Click **Embed** (tests Ollama's `bge-m3` - first real cross-service
   call; if this fails, Ollama is the most likely culprit).
4. Click **Store** (tests Postgres/pgvector write path).
5. **Query tab** - type a question you know the PDF answers, click
   **Run Full Pipeline**. Watch the progress rail move through stages
   6-12. Stage 12 should render a cited answer within ~10-30s (first
   call to qwen2.5:7b may be slower - model load into memory).

If step 5 completes with a sensible answer, every layer is wired
correctly.

---

## 7. Common failure modes (all hit and diagnosed during development)

| Symptom | Cause | Fix |
|---|---|---|
| Embed/Search/Answer fail with connection errors, Convert/Chunk still work | Ollama not running (stops silently after machine restarts) | `open -a Ollama`, re-check `curl localhost:11434/api/tags` |
| `/documents` or any DB-touching endpoint 500s | Postgres not running | `brew services start postgresql@17`, re-check `pg_isready` |
| Stage 10 (No-Answer Detection) says "no answer" for a question the PDF clearly answers | This app fixed a real bug here: RRF-score-only detection can't distinguish "real answer found by only one search method" from "garbage found by neither" - both score identically. Fixed via a `similarity_floor` backup check (Stage 10 has two adjustable thresholds in the GUI, not one) | If retuning thresholds, re-run `app/eval/eval_set_v1.json` via the RAG Eval tab and confirm no regressions before trusting new values |
| Keyword search (Stage 8) misses an exact-looking phrase | PostgreSQL FTS tokenization can split on characters your eye doesn't register (e.g. a stray space from PDF extraction: "16 th Finance Commission" vs "16th Finance Commission") | Known/expected FTS behavior, not a bug - semantic search (Stage 7) or hybrid fusion (Stage 9) usually recovers it |
| `pip install` fails on `torch` | Wrong Python version or architecture mismatch | Confirm `python3 --version` is 3.12.x and you're on the venv's pip, not system pip |
| Backend starts but GUI is unstyled/broken | Opened `index.html` directly as a file instead of via the server | Must load via `http://localhost:8000`, not `file://...index.html` - the page fetches from relative API paths |

---

## 8. Project structure reference

```text
RAG Casestudy/
  SETUP.md                    <- this file
  app/
    backend/
      main.py                 FastAPI app + all HTTP endpoints
      requirements.txt        pip dependencies (see step 4)
      docling_parser.py       Stage 1: PDF -> structured doc
      chunker.py               Stage 2: header-aware chunking + token counting
      embedder.py              Stage 3: bge-m3 via Ollama /api/embed
      vectorstore.py           Stage 4/5: Postgres/pgvector reads+writes
      query_processing.py      Stage 6: query normalization
      fusion.py                 Stage 9: Reciprocal Rank Fusion
      no_answer.py              Stage 10: no-answer detection (RRF + similarity floor)
      context_builder.py        Stage 11: dedup/merge/token-budget/citation tags
      answer_generator.py       Stage 12: prompt build + qwen2.5:7b call
      eval_runner.py             Stage 13: background batch eval runner
    eval/
      eval_set_v1.json          structured eval questions (used by Stage 13 GUI)
      eval_set_v1.md             hand-run eval log/notes (human-readable history)
    frontend/
      index.html                entire GUI - single file, no build step, no
                                  external font/JS CDN dependencies
    uploads/, outputs/, embeddings_tmp/   gitignored runtime artifacts
    venv/                        gitignored Python virtualenv
```

No `.env` file exists or is required - all config (DB URL, Ollama URL,
model names, ports) is hardcoded directly in the relevant `.py` file,
listed here so nothing needs guessing:

| Setting | Value | File |
|---|---|---|
| Postgres connection | `postgresql://localhost/rag_casestudy` | `vectorstore.py` |
| Ollama embed endpoint | `http://localhost:11434/api/embed` | `embedder.py` |
| Ollama chat endpoint | `http://localhost:11434/api/chat` | `answer_generator.py` |
| Embedding model | `bge-m3` | `embedder.py` |
| Answer model | `qwen2.5:7b` | `answer_generator.py` |
| Backend port | `8000` (via `uvicorn ... --port 8000`) | run command, not hardcoded in code |

---

## 9. Resetting to a clean state

To wipe all stored documents/chunks without dropping the schema:
```bash
psql -d rag_casestudy -c "TRUNCATE documents, chunks RESTART IDENTITY CASCADE;"
```

To remove everything including the schema (start over from step 2a):
```bash
dropdb rag_casestudy
createdb rag_casestudy
```
