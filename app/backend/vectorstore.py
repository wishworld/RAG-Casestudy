"""Stage 5: persist chunks + embeddings in Postgres/pgvector and search
them with SQL, replacing the in-memory dict used during Stages 2-4."""

import numpy as np
import psycopg
from pgvector.psycopg import register_vector

DB_URL = "postgresql://localhost/rag_casestudy"


def get_connection():
    conn = psycopg.connect(DB_URL, autocommit=True)
    register_vector(conn)
    return conn


def upsert_document(job_id: str, filename: str) -> int:
    """Inserts a document row (or returns the existing one for this
    job_id) and returns its id."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (job_id, filename)
                VALUES (%s, %s)
                ON CONFLICT (job_id) DO UPDATE SET filename = EXCLUDED.filename
                RETURNING id
                """,
                (job_id, filename),
            )
            return cur.fetchone()[0]


def store_chunks(job_id: str, filename: str, embedded_chunks: list[dict]) -> list[dict]:
    """Stores embedded chunks for a document. Returns per-chunk statuses
    ({"chunk_id", "chunk_index", "status": "ok"|"failed", "error"?}) so
    the caller can tell storage failures apart from embedding failures.

    The document row is only created/kept if at least one chunk actually
    stored - otherwise a failed store would leave a "ghost" document with
    0 chunks in the documents list."""
    statuses = []

    with get_connection() as conn:
        document_id = upsert_document(job_id, filename)

        for c in embedded_chunks:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO chunks (
                            chunk_id, document_id, chunk_index, source_file,
                            page_number, section_heading, content_type,
                            token_count, text, has_overlap, overlap_text, embedding
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (chunk_id) DO UPDATE SET
                            embedding = EXCLUDED.embedding,
                            text = EXCLUDED.text
                        """,
                        (
                            c["chunk_id"], document_id, c["chunk_index"], c["source_file"],
                            c["page_number"], c["section_heading"], c["content_type"],
                            c["token_count"], c["text"], c["has_overlap"], c["overlap_text"],
                            c["embedding"],
                        ),
                    )
                statuses.append({"chunk_id": c["chunk_id"], "chunk_index": c["chunk_index"], "status": "ok"})
            except Exception as e:
                statuses.append({
                    "chunk_id": c["chunk_id"], "chunk_index": c["chunk_index"],
                    "status": "failed", "error": str(e),
                })

        if not any(s["status"] == "ok" for s in statuses):
            with conn.cursor() as cur:
                cur.execute("DELETE FROM documents WHERE id = %s", (document_id,))

    return statuses


def search(query_vector: list[float], top_k: int = 5, job_id: str | None = None) -> list[dict]:
    """Cosine-similarity search via pgvector's <=> operator (indexed by
    the HNSW index on chunks.embedding). If job_id is given, restricts
    the search to that document only."""
    # psycopg's pgvector adapter only recognizes numpy arrays as the
    # `vector` type - a plain Python list falls through to a generic
    # array type and the <=> operator lookup fails.
    query_vector = np.asarray(query_vector, dtype=np.float32)

    sql = """
        SELECT c.chunk_id, c.chunk_index, c.source_file, c.page_number,
               c.section_heading, c.content_type, c.token_count, c.text,
               c.has_overlap, c.overlap_text,
               1 - (c.embedding <=> %s) AS similarity
        FROM chunks c
    """
    params = [query_vector]

    if job_id:
        sql += " JOIN documents d ON d.id = c.document_id WHERE d.job_id = %s"
        params.append(job_id)

    sql += " ORDER BY c.embedding <=> %s LIMIT %s"
    params.extend([query_vector, top_k])

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]


def search_keyword(query: str, top_k: int = 5, job_id: str | None = None) -> list[dict]:
    """Stage 8: keyword search via PostgreSQL full-text search. Uses the
    search_vector column (tsvector, auto-maintained by a DB trigger on
    chunks.text) and ts_rank to score matches - exact/lexical matching,
    complementary to the semantic search() above rather than a
    replacement for it (e.g. good at exact codes like "error 91")."""
    sql = """
        SELECT c.chunk_id, c.chunk_index, c.source_file, c.page_number,
               c.section_heading, c.content_type, c.token_count, c.text,
               c.has_overlap, c.overlap_text,
               ts_rank(c.search_vector, websearch_to_tsquery('english', %s)) AS keyword_rank
        FROM chunks c
        WHERE c.search_vector @@ websearch_to_tsquery('english', %s)
    """
    params = [query, query]

    if job_id:
        sql += " AND c.document_id IN (SELECT id FROM documents WHERE job_id = %s)"
        params.append(job_id)

    sql += " ORDER BY keyword_rank DESC LIMIT %s"
    params.append(top_k)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]


def list_documents() -> list[dict]:
    """Returns every stored document with its chunk count, newest first."""
    sql = """
        SELECT d.job_id, d.filename, d.uploaded_at, count(c.id) AS chunk_count
        FROM documents d
        LEFT JOIN chunks c ON c.document_id = d.id
        GROUP BY d.id, d.job_id, d.filename, d.uploaded_at
        ORDER BY d.uploaded_at DESC
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def delete_document(job_id: str) -> dict:
    """Deletes one document and its chunks (cascade). Returns counts, or
    chunks_deleted=-1 if no document matched the job_id."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM documents WHERE job_id = %s", (job_id,))
            row = cur.fetchone()
            if not row:
                return {"deleted": False, "chunks_deleted": 0}
            document_id = row[0]

            cur.execute("SELECT count(*) FROM chunks WHERE document_id = %s", (document_id,))
            chunk_count = cur.fetchone()[0]

            cur.execute("DELETE FROM documents WHERE id = %s", (document_id,))

    return {"deleted": True, "chunks_deleted": chunk_count}


def delete_all() -> dict:
    """Wipes every document and chunk from the store. Destructive and
    unscoped - used by the admin reset action, not per-document deletes."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM documents")
            doc_count = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM chunks")
            chunk_count = cur.fetchone()[0]
            cur.execute("TRUNCATE documents, chunks RESTART IDENTITY CASCADE")
    return {"documents_deleted": doc_count, "chunks_deleted": chunk_count}


def get_chunks_for_job(job_id: str) -> list[dict]:
    """Returns all chunks (without embeddings) for a given job_id, in order."""
    sql = """
        SELECT c.chunk_id, c.chunk_index, c.source_file, c.page_number,
               c.section_heading, c.content_type, c.token_count, c.text,
               c.has_overlap, c.overlap_text
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE d.job_id = %s
        ORDER BY c.chunk_index
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (job_id,))
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]
