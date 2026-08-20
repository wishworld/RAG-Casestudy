"""Stage 13: evaluation harness.

Runs a batch of questions (with known-correct expectations) through the
FULL pipeline - Stages 6 through 12, including the LLM answer - and
scores each one automatically instead of a human eyeballing results one
at a time (as was done by hand for app/eval/eval_set_v1.md).

Runs as a background job (a single eval run of ~14 questions through
the LLM takes minutes; 50-100 questions would take much longer) so the
GUI can poll progress instead of blocking on one request.
"""

import threading
import time
import uuid

from query_processing import normalize_query
from embedder import embed_texts
from fusion import reciprocal_rank_fusion
from no_answer import check_no_answer, DEFAULT_RRF_THRESHOLD, DEFAULT_SIMILARITY_FLOOR
from context_builder import build_context, DEFAULT_TOKEN_BUDGET
from answer_generator import generate_answer
import vectorstore

CANDIDATE_POOL = 30
TOP_K = 5

# In-memory job store - fine for a single-user local tool, matches the
# existing pattern of _chunks_by_job in main.py.
_jobs: dict[str, dict] = {}


def start_eval_run(questions: list[dict]) -> str:
    """Kicks off a background thread, returns a job_id immediately so
    the caller can poll /eval/status/{job_id} without blocking."""
    job_id = uuid.uuid4().hex[:8]
    _jobs[job_id] = {
        "status": "running",
        "total": len(questions),
        "completed": 0,
        "results": [],
        "started_at": time.time(),
        "finished_at": None,
    }
    thread = threading.Thread(target=_run_eval, args=(job_id, questions), daemon=True)
    thread.start()
    return job_id


def get_eval_status(job_id: str) -> dict | None:
    return _jobs.get(job_id)


def _run_eval(job_id: str, questions: list[dict]):
    job = _jobs[job_id]
    for q in questions:
        result = _run_one_question(q)
        job["results"].append(result)
        job["completed"] += 1
    job["status"] = "done"
    job["finished_at"] = time.time()


def _run_one_question(q: dict) -> dict:
    """Runs one question through Stages 6-12 and scores it against the
    expectations in q. Never raises - a failure in any stage is
    recorded as a result field, so one bad question doesn't kill the
    whole batch run."""
    question_id = q["id"]
    question_text = q["question"]

    try:
        cleaned_query = normalize_query(question_text)

        query_vector = embed_texts([cleaned_query])[0]
        semantic_results = vectorstore.search(query_vector, top_k=CANDIDATE_POOL)
        keyword_results = vectorstore.search_keyword(cleaned_query, top_k=CANDIDATE_POOL)
        fused = reciprocal_rank_fusion([semantic_results, keyword_results], top_k=TOP_K)

        no_answer = check_no_answer(
            fused, rrf_threshold=DEFAULT_RRF_THRESHOLD, similarity_floor=DEFAULT_SIMILARITY_FLOOR
        )

        # Retrieval scoring: did the expected section show up anywhere
        # in the top-K, not just at rank 1 - matches how Recall@K is
        # defined in the research notes.
        expected_section = q.get("expected_section_contains")
        retrieval_pass = None
        if expected_section:
            retrieval_pass = any(
                expected_section.lower() in (r.get("section_heading") or "").lower()
                for r in fused
            )

        no_answer_pass = no_answer["has_answer"] == q.get("should_have_answer", True)

        answer_text = None
        answer_pass = None
        elapsed_llm = None
        if no_answer["has_answer"] and fused:
            context = build_context(fused, token_budget=DEFAULT_TOKEN_BUDGET)
            llm_start = time.time()
            answer_result = generate_answer(cleaned_query, context["blocks"])
            elapsed_llm = round(time.time() - llm_start, 1)
            if "error" not in answer_result:
                answer_text = answer_result["answer"]
                expected_fragment = q.get("expected_answer_contains")
                if expected_fragment:
                    answer_pass = expected_fragment.lower() in answer_text.lower()

        return {
            "id": question_id,
            "question": question_text,
            "retrieval_pass": retrieval_pass,
            "no_answer_pass": no_answer_pass,
            "has_answer": no_answer["has_answer"],
            "top_section": fused[0]["section_heading"] if fused else None,
            "answer": answer_text,
            "answer_pass": answer_pass,
            "elapsed_llm_seconds": elapsed_llm,
            "error": None,
        }
    except Exception as e:
        return {
            "id": question_id,
            "question": question_text,
            "retrieval_pass": None,
            "no_answer_pass": None,
            "has_answer": None,
            "top_section": None,
            "answer": None,
            "answer_pass": None,
            "elapsed_llm_seconds": None,
            "error": str(e),
        }


def summarize(results: list[dict]) -> dict:
    """Aggregates individual results into a scorecard."""
    total = len(results)
    retrieval_checked = [r for r in results if r["retrieval_pass"] is not None]
    retrieval_passed = sum(1 for r in retrieval_checked if r["retrieval_pass"])

    no_answer_checked = [r for r in results if r["no_answer_pass"] is not None]
    no_answer_passed = sum(1 for r in no_answer_checked if r["no_answer_pass"])

    answer_checked = [r for r in results if r["answer_pass"] is not None]
    answer_passed = sum(1 for r in answer_checked if r["answer_pass"])

    errors = sum(1 for r in results if r["error"])

    return {
        "total": total,
        "errors": errors,
        "retrieval": {"passed": retrieval_passed, "checked": len(retrieval_checked)},
        "no_answer_detection": {"passed": no_answer_passed, "checked": len(no_answer_checked)},
        "answer_quality": {"passed": answer_passed, "checked": len(answer_checked)},
    }
