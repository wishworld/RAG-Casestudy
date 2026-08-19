"""Stage 9: Reciprocal Rank Fusion (RRF).

Combines two independently-ranked result lists (semantic + keyword) into
one ranked list, using rank POSITION rather than raw scores - cosine
similarity and ts_rank live on different scales and aren't comparable
directly, but "1st place" vs "3rd place" is.

RRF = sum(1 / (k + rank)) across every list a chunk appears in, rank
starting at 1. k=60 is the standard starting constant from the original
RRF paper - not tuned for this project, just the documented default.
"""

RRF_K = 60


def reciprocal_rank_fusion(
    result_lists: list[list[dict]],
    key: str = "chunk_id",
    top_k: int = 10,
) -> list[dict]:
    """result_lists: e.g. [semantic_results, keyword_results], each
    already ranked best-first. Returns fused list, best-first, each item
    carrying the original chunk fields plus rrf_score and per-source
    ranks (semantic_rank / keyword_rank_position) for eyeballing."""
    scores: dict[str, float] = {}
    chunks_by_key: dict[str, dict] = {}
    source_ranks: dict[str, dict[int, int]] = {}

    for source_index, results in enumerate(result_lists):
        for rank, item in enumerate(results, start=1):
            chunk_key = item[key]
            scores[chunk_key] = scores.get(chunk_key, 0.0) + 1.0 / (RRF_K + rank)
            chunks_by_key.setdefault(chunk_key, item)
            source_ranks.setdefault(chunk_key, {})[source_index] = rank

    source_labels = ["semantic", "keyword"]

    fused = []
    for chunk_key, score in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:top_k]:
        ranks = source_ranks[chunk_key]
        # Visible arithmetic, e.g. "1/(60+1) + 1/(60+3) = 0.03279" - built
        # from the same ranks used to compute the score above, so this
        # is a direct readout, not a re-derivation that could drift.
        terms = [f"1/({RRF_K}+{rank})" for rank in ranks.values()]
        formula = f"{' + '.join(terms)} = {round(score, 5)}"
        sources_used = ", ".join(
            f"{source_labels[i]} rank {rank}" for i, rank in sorted(ranks.items())
        )

        fused.append({
            **chunks_by_key[chunk_key],
            "rrf_score": round(score, 5),
            "found_in_semantic": 0 in ranks,
            "found_in_keyword": 1 in ranks,
            "semantic_rank": ranks.get(0),
            "keyword_rank_position": ranks.get(1),
            "rrf_formula": formula,
            "rrf_sources": sources_used,
        })

    return fused
