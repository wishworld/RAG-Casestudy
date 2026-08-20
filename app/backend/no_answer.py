"""Stage 10: no-answer detection.

Top-K retrieval always returns something, even when nothing in the
store actually answers the question - it just returns the "least bad"
matches. This checks whether the top result is a real answer or just
the least-bad guess.

v1 (RRF-score-only) had a confirmed bug, found via a 14-question eval
against Union_Budget_Analysis-2026-27.pdf (app/eval/eval_set_v1.md):
RRF score alone can't tell "a real answer found by only ONE search
method" apart from "garbage found by neither" - both land on exactly
1/(60+1) = 0.01639 when only semantic search returns anything, because
RRF only rewards AGREEMENT between sources, not match confidence. This
produced a ~56% false-negative rate (5 of 9 real answers wrongly
rejected).

v2 fixes this by also checking raw semantic similarity (Stage 7's
score, 0-1 scale) as an independent pass condition - a confident
semantic-only match can now pass on its own merit instead of being
punished for keyword search missing it. Calibrated from the same
eval run: real answers scored 0.4867-0.7176 similarity, garbage
scored 0.4122-0.4247 - a clean gap, with 0.45 sitting in the middle.
Both thresholds are still small-sample guesses, exposed as adjustable
GUI inputs, meant to be recalibrated once Stage 13 (a larger
evaluation harness) exists.
"""

DEFAULT_RRF_THRESHOLD = 0.02
DEFAULT_SIMILARITY_FLOOR = 0.45


def check_no_answer(
    results: list[dict],
    rrf_threshold: float = DEFAULT_RRF_THRESHOLD,
    similarity_floor: float = DEFAULT_SIMILARITY_FLOOR,
) -> dict:
    """has_answer is True if the top result clears EITHER bar:
    - rrf_score >= rrf_threshold (both sources agree), or
    - similarity >= similarity_floor (confident on its own, even if
      only one source found it)
    Returns {"has_answer", "top_score", "top_similarity",
    "rrf_threshold", "similarity_floor", "passed_count", "total_count"}."""
    if not results:
        return {
            "has_answer": False, "top_score": None, "top_similarity": None,
            "rrf_threshold": rrf_threshold, "similarity_floor": similarity_floor,
            "passed_count": 0, "total_count": 0,
        }

    def passes(r):
        return r["rrf_score"] >= rrf_threshold or r.get("similarity", 0) >= similarity_floor

    top = results[0]
    return {
        "has_answer": passes(top),
        "top_score": top["rrf_score"],
        "top_similarity": top.get("similarity"),
        "rrf_threshold": rrf_threshold,
        "similarity_floor": similarity_floor,
        "passed_count": sum(1 for r in results if passes(r)),
        "total_count": len(results),
    }
