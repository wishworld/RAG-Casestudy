"""FastAPI backend: upload a PDF, get back cleaned Markdown (Docling),
retrieval chunks, embeddings, and pgvector-backed search over those chunks."""

import json
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from docling_parser import parse_to_markdown as docling_parse, parse_document
from chunker import chunk_document
from embedder import embed_texts
from query_processing import normalize_query
from fusion import reciprocal_rank_fusion
from no_answer import check_no_answer, DEFAULT_RRF_THRESHOLD, DEFAULT_SIMILARITY_FLOOR
from context_builder import build_context, DEFAULT_TOKEN_BUDGET
from answer_generator import generate_answer
import vectorstore

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
FRONTEND_DIR = BASE_DIR / "frontend"
EMBEDDINGS_TMP_DIR = BASE_DIR / "embeddings_tmp"
EMBEDDINGS_TMP_DIR.mkdir(exist_ok=True)

app = FastAPI(title="PDF to Markdown - Stage 1")

# Transient store for chunks between the Chunk and Embed button clicks.
# Embedded chunks (Stage 3) land in embeddings_tmp/{job_id}.json until the
# user explicitly clicks Store (Stage 6), which writes them to Postgres.
_chunks_by_job: dict[str, list[dict]] = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.post("/convert")
async def convert_pdf(file: UploadFile = File(...)):
    job_id = uuid.uuid4().hex[:8]
    pdf_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    pdf_path.write_bytes(await file.read())

    start = time.time()
    markdown = docling_parse(str(pdf_path))
    elapsed = round(time.time() - start, 1)

    md_path = OUTPUT_DIR / f"{job_id}_{Path(file.filename).stem}.md"
    md_path.write_text(markdown)

    return {
        "job_id": job_id,
        "filename": file.filename,
        "elapsed_seconds": elapsed,
        "markdown": markdown,
    }


@app.post("/chunk")
async def chunk_pdf(file: UploadFile = File(...)):
    job_id = uuid.uuid4().hex[:8]
    pdf_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    pdf_path.write_bytes(await file.read())

    start = time.time()
    doc = parse_document(str(pdf_path))
    chunks = chunk_document(doc, file.filename)
    elapsed = round(time.time() - start, 1)

    _chunks_by_job[job_id] = chunks

    return {
        "job_id": job_id,
        "filename": file.filename,
        "chunk_count": len(chunks),
        "elapsed_seconds": elapsed,
        "chunks": chunks,
    }


@app.post("/embed")
async def embed_job(job_id: str = Form(...)):
    """Stage 3: generates embeddings and writes them to a temp file.
    Does NOT touch Postgres - that only happens when the user explicitly
    clicks Store (Stage 6, see /store below)."""
    chunks = _chunks_by_job.get(job_id)
    if not chunks:
        return {"error": f"No chunks found for job_id={job_id}. Run /chunk first."}

    start = time.time()
    statuses = []
    embedded = []
    try:
        # One batched call for all chunks (fast, avoids the 1-call-per-item
        # pattern from Stage 1) - if the batch itself fails, every chunk
        # is reported as failed below instead of silently losing the run.
        vectors = embed_texts([c["text"] for c in chunks])
        for chunk, vector in zip(chunks, vectors):
            embedded.append({**chunk, "embedding": vector})
            statuses.append({"chunk_id": chunk["chunk_id"], "chunk_index": chunk["chunk_index"], "status": "ok"})
    except Exception as e:
        for chunk in chunks:
            statuses.append({
                "chunk_id": chunk["chunk_id"],
                "chunk_index": chunk["chunk_index"],
                "status": "failed",
                "error": str(e),
            })

    if embedded:
        tmp_path = EMBEDDINGS_TMP_DIR / f"{job_id}.json"
        tmp_path.write_text(json.dumps(embedded))

    elapsed = round(time.time() - start, 1)

    return {
        "job_id": job_id,
        "embedded_count": len(embedded),
        "failed_count": len(statuses) - len(embedded),
        "elapsed_seconds": elapsed,
        "statuses": statuses,
    }


@app.post("/store")
async def store_job(job_id: str = Form(...)):
    """Stage 6: reads the embeddings temp file and writes it into
    Postgres/pgvector. Explicit, user-triggered - not automatic."""
    tmp_path = EMBEDDINGS_TMP_DIR / f"{job_id}.json"
    if not tmp_path.exists():
        return {"error": f"No embeddings found for job_id={job_id}. Run /embed first."}

    embedded = json.loads(tmp_path.read_text())
    if not embedded:
        return {"error": f"Embeddings file for job_id={job_id} is empty."}

    start = time.time()
    filename = embedded[0]["source_file"]
    statuses = vectorstore.store_chunks(job_id, filename, embedded)
    elapsed = round(time.time() - start, 1)

    stored_count = sum(1 for s in statuses if s["status"] == "ok")

    return {
        "job_id": job_id,
        "stored_count": stored_count,
        "failed_count": len(statuses) - stored_count,
        "elapsed_seconds": elapsed,
        "statuses": statuses,
    }


@app.post("/query/normalize")
async def query_normalize(query: str = Form(...)):
    """Stage 6: preview-only endpoint - shows the cleaned query without
    running a search, so normalization can be eyeballed on its own."""
    cleaned = normalize_query(query)
    return {"raw_query": query, "normalized_query": cleaned, "changed": cleaned != query}


@app.post("/search")
async def search_chunks(query: str = Form(...), job_id: str | None = Form(None), top_k: int = Form(5)):
    """Searches the pgvector store. With no job_id, searches across every
    stored document; pass job_id to scope to one document."""
    cleaned_query = normalize_query(query)
    query_vector = embed_texts([cleaned_query])[0]
    results = vectorstore.search(query_vector, top_k=top_k, job_id=job_id)

    if not results:
        return {"error": "No results. Store at least one document first."}

    for r in results:
        r["similarity"] = round(r["similarity"], 4)

    return {"job_id": job_id, "query": cleaned_query, "results": results}


@app.post("/search/keyword")
async def search_keyword_chunks(query: str = Form(...), job_id: str | None = Form(None), top_k: int = Form(5)):
    """Stage 8: keyword search via PostgreSQL full-text search (no
    embedding call - lexical matching only)."""
    cleaned_query = normalize_query(query)
    results = vectorstore.search_keyword(cleaned_query, top_k=top_k, job_id=job_id)

    if not results:
        return {"error": "No keyword matches. Try different terms, or store a document first."}

    for r in results:
        r["keyword_rank"] = round(r["keyword_rank"], 4)

    return {"job_id": job_id, "query": cleaned_query, "results": results}


@app.post("/search/fuse")
async def search_fuse(
    semantic_results: str = Form(...),
    keyword_results: str = Form(...),
    top_k: int = Form(5),
    rrf_threshold: float = Form(DEFAULT_RRF_THRESHOLD),
    similarity_floor: float = Form(DEFAULT_SIMILARITY_FLOOR),
):
    """Stage 9 (reuse path): fuses two ALREADY-COMPUTED result lists via
    RRF - no DB calls, no re-embedding. Lets the GUI pass Stage 7's and
    Stage 8's last-displayed results directly instead of Stage 9 quietly
    re-running both searches from scratch."""
    semantic = json.loads(semantic_results)
    keyword = json.loads(keyword_results)

    if not semantic and not keyword:
        return {"error": "No results to fuse. Run Stage 7 and/or Stage 8 first."}

    fused = reciprocal_rank_fusion([semantic, keyword], top_k=top_k)
    no_answer = check_no_answer(fused, rrf_threshold=rrf_threshold, similarity_floor=similarity_floor)

    return {
        "semantic_count": len(semantic),
        "keyword_count": len(keyword),
        "results": fused,
        "no_answer": no_answer,
    }


@app.post("/search/hybrid")
async def search_hybrid(
    query: str = Form(...),
    job_id: str | None = Form(None),
    top_k: int = Form(5),
    rrf_threshold: float = Form(DEFAULT_RRF_THRESHOLD),
    similarity_floor: float = Form(DEFAULT_SIMILARITY_FLOOR),
):
    """Stage 9: fuses Stage 7 (semantic) and Stage 8 (keyword) results
    via Reciprocal Rank Fusion. Pulls a wider candidate pool (30) from
    each source before fusing down to top_k, so fusion has enough
    overlap to work with."""
    cleaned_query = normalize_query(query)
    candidate_pool = 30

    query_vector = embed_texts([cleaned_query])[0]
    semantic_results = vectorstore.search(query_vector, top_k=candidate_pool, job_id=job_id)
    keyword_results = vectorstore.search_keyword(cleaned_query, top_k=candidate_pool, job_id=job_id)

    if not semantic_results and not keyword_results:
        return {"error": "No results from either source. Store at least one document first."}

    fused = reciprocal_rank_fusion([semantic_results, keyword_results], top_k=top_k)
    no_answer = check_no_answer(fused, rrf_threshold=rrf_threshold, similarity_floor=similarity_floor)

    return {
        "job_id": job_id,
        "query": cleaned_query,
        "semantic_count": len(semantic_results),
        "keyword_count": len(keyword_results),
        "results": fused,
        "no_answer": no_answer,
    }


@app.post("/context/build")
async def context_build(
    chunks: str = Form(...),
    token_budget: int = Form(DEFAULT_TOKEN_BUDGET),
):
    """Stage 11: takes Stage 9/10's surviving chunks (as JSON, passed
    from the GUI - no DB call, pure transformation) and prepares them
    for the LLM prompt: dedupe, merge adjacent chunks, restore document
    order, apply a token budget, tag with citation markers."""
    parsed = json.loads(chunks)
    if not parsed:
        return {"error": "No chunks to build context from. Run Stage 9 first."}

    result = build_context(parsed, token_budget=token_budget)
    return result


@app.post("/answer")
async def answer_question(question: str = Form(...), blocks: str = Form(...)):
    """Stage 12: takes Stage 11's citation-tagged blocks (as JSON) and
    the original question, builds a grounded prompt, calls qwen2.5:7b
    via Ollama, returns the answer plus the exact prompt sent (for
    eyeballing what the model actually saw)."""
    parsed_blocks = json.loads(blocks)

    start = time.time()
    result = generate_answer(question, parsed_blocks)
    elapsed = round(time.time() - start, 1)

    if "error" in result:
        return {"error": result["error"], "elapsed_seconds": elapsed}

    return {
        "question": question,
        "answer": result["answer"],
        "prompt": result["prompt"],
        "elapsed_seconds": elapsed,
    }


@app.get("/documents")
async def list_documents():
    documents = vectorstore.list_documents()
    for d in documents:
        d["uploaded_at"] = d["uploaded_at"].isoformat()
    return {"documents": documents}


@app.post("/documents/{job_id}/delete")
async def delete_document(job_id: str):
    result = vectorstore.delete_document(job_id)
    _chunks_by_job.pop(job_id, None)
    (EMBEDDINGS_TMP_DIR / f"{job_id}.json").unlink(missing_ok=True)
    return result


@app.post("/admin/delete_all")
async def delete_all_data(confirm: str = Form(...)):
    """Wipes every document and chunk from Postgres. Destructive and
    unscoped - requires the literal string 'DELETE' to guard against
    accidental calls."""
    if confirm != "DELETE":
        return {"error": "Confirmation string did not match. Send confirm=DELETE to proceed."}

    result = vectorstore.delete_all()
    _chunks_by_job.clear()
    for f in EMBEDDINGS_TMP_DIR.glob("*.json"):
        f.unlink()

    return {"status": "ok", **result}
