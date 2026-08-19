# App Run Checklist

Everything that must be active for the RAG app to work end to end.
Check in this order - each step depends on the one above it.

```text
1. Ollama service
   |
   v
2. Required models pulled (bge-m3, qwen2.5:7b)
   |
   v
3. PostgreSQL service
   |
   v
4. pgvector extension + schema (one-time setup, not a per-run step)
   |
   v
5. FastAPI backend (uvicorn)
   |
   v
6. Browser tab open to localhost:8000
```

## 1. Ollama service

Check:
```bash
curl -s -m 3 http://localhost:11434/api/tags
```
If not reachable:
```bash
open -a Ollama
```

## 2. Required models

Check:
```bash
ollama list
```
Must show both `bge-m3` and `qwen2.5:7b`. If missing:
```bash
ollama pull bge-m3
ollama pull qwen2.5:7b
```

## 3. PostgreSQL service

Check:
```bash
pg_isready -h localhost
brew services list | grep postgresql
```
If not running:
```bash
brew services start postgresql@17
```

## 4. pgvector extension + schema

One-time setup only - not needed on every run. Confirm it still exists if
you ever recreate the database:
```bash
psql -d rag_casestudy -c "SELECT extname, extversion FROM pg_extension;"
psql -d rag_casestudy -c "\dt"
```
Should show `vector` extension and `documents` / `chunks` tables.

## 5. FastAPI backend

Check:
```bash
lsof -i :8000
curl -s -m 3 http://localhost:8000/documents
```
If not running:
```bash
cd app/backend
uvicorn main:app --reload --port 8000
```

## 6. Open the app

```
http://localhost:8000
```

## Quick all-in-one health check

```bash
echo "Ollama:" && curl -s -m 3 http://localhost:11434/api/tags -o /dev/null -w "%{http_code}\n"
echo "Postgres:" && pg_isready -h localhost
echo "Backend:" && curl -s -m 3 http://localhost:8000/documents -o /dev/null -w "%{http_code}\n"
```
All three should return `200` / `accepting connections`. If any fails,
fix that layer before testing the app - failures cascade downward
(no Ollama breaks Embed/Search even if Convert still works, since
Convert/Docling doesn't call Ollama but Embed and Search do).
