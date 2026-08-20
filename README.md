# RAG Case Study

A local, privacy-first RAG (Retrieval-Augmented Generation) pipeline built
from scratch - no LangChain, no framework hiding the internals. Every
stage (parse, chunk, embed, store, semantic search, keyword search,
hybrid fusion, no-answer detection, context construction, LLM answer,
evaluation) is exposed as its own button in the GUI, individually
triggerable and inspectable.

Built to answer one question as a Product Manager: what actually
happens between "upload a document" and "get a grounded answer" -
and which of those decisions would I actually want to intervene on?

## Why this exists

Using a good RAG product (like Google's NotebookLM) is one thing.
Understanding the decisions underneath it is another. Most RAG
tutorials and frameworks bundle all of this into a single function
call - you get an answer, but never see what happened in between.

This project keeps every stage as its own testable step on purpose,
so you can watch semantic search and keyword search disagree, see
Reciprocal Rank Fusion resolve that disagreement, watch a no-answer
check catch a bad retrieval before it reaches the LLM, and run an
automated evaluation set to prove (or disprove) that a fix actually
helped - not just eyeball one good-looking demo.

## What's in the pipeline

```text
Input tab  (index a document, once)
  Stage 1  Parse       PDF -> structured Markdown (Docling)
  Stage 2  Chunk       header-aware split into retrieval-sized pieces
  Stage 3  Embed       bge-m3 (Ollama) -> 1024-dim vectors
  Stage 4  Store       Postgres + pgvector

Query tab  (ask a question, every time)
  Stage 6  Normalize          unicode + whitespace cleanup
  Stage 7  Semantic search    pgvector cosine similarity
  Stage 8  Keyword search     PostgreSQL full-text search
  Stage 9  Hybrid fusion      Reciprocal Rank Fusion (RRF)
  Stage 10 No-answer check    RRF score + similarity floor
  Stage 11 Context build      dedup, merge, token budget, citations
  Stage 12 Answer generation  qwen2.5:7b (Ollama), grounded + cited

RAG Eval tab
  Stage 13 Batch evaluation   scores retrieval, no-answer detection,
                              and answer quality automatically
```

A "Run Full Pipeline" button chains Stages 6-12 for a normal question;
every stage's own button still works independently for debugging.

## A real bug this caught

Stage 10's first version scored "no answer" using only the RRF fusion
score. That score turned out unable to tell "a real answer found by
just one search method" apart from "garbage found by neither" - both
landed on the exact same number, producing a ~56% false-negative rate
on paraphrased questions. Fixed with an independent similarity-floor
check, verified against a real eval set. Details in
[app/eval/eval_set_v1.md](app/eval/eval_set_v1.md).

## Stack

Python (FastAPI) backend, single-file HTML/CSS/JS frontend (no build
step), PostgreSQL + pgvector for storage, Ollama for local models
(`bge-m3` for embeddings, `qwen2.5:7b` for answers) - everything runs
on your own machine, nothing leaves it.

## Try it

Full setup instructions (installs, schema, exact versions,
troubleshooting) are in **[SETUP.md](SETUP.md)** - written so it can
be followed from zero with no prior context. Short version:

```bash
brew install postgresql@17 pgvector ollama
ollama pull bge-m3 && ollama pull qwen2.5:7b
createdb rag_casestudy   # then run the schema in SETUP.md step 2a

cd app
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt

cd backend
uvicorn main:app --reload --port 8000
```

Then open `http://localhost:8000` - upload a PDF on the Input tab,
ask a question on the Query tab, or read the **Learn RAG** tab for a
plain-English walkthrough of every concept mapped to the stage that
teaches it.

## Project structure

```text
app/
  backend/     FastAPI app + one module per pipeline stage
  frontend/    the entire GUI (single HTML file)
  eval/        evaluation question sets
SETUP.md       full setup guide
```

## Status

This is a learning project, not a production system - built to
understand RAG internals, not to ship. No `.env` file or credentials
are required; all local config is documented in
[SETUP.md](SETUP.md#8-project-structure-reference).
