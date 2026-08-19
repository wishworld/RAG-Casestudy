"""Stage 3: turn chunk text into vectors using bge-m3 (via Ollama).

bge-m3: 1024-dim, 8192-token context, MIT license, strong multilingual
(including Hindi) retrieval performance - verified via `ollama show bge-m3`.
Uses Ollama's native /api/embed endpoint, which accepts a batch of inputs
in one call rather than one request per chunk.
"""

import requests

OLLAMA_URL = "http://localhost:11434/api/embed"
MODEL = "bge-m3"
EMBEDDING_DIM = 1024


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embeds a batch of texts in a single request. Returns one vector
    per input text, in the same order."""
    if not texts:
        return []
    response = requests.post(OLLAMA_URL, json={"model": MODEL, "input": texts})
    response.raise_for_status()
    return response.json()["embeddings"]


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Adds an 'embedding' field to each chunk dict, in place semantics
    (returns new list of dicts with embeddings attached)."""
    texts = [c["text"] for c in chunks]
    vectors = embed_texts(texts)
    return [{**chunk, "embedding": vector} for chunk, vector in zip(chunks, vectors)]
