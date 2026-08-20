"""Stage 11: context construction.

Takes Stage 9/10's surviving chunks (already ranked by relevance) and
prepares them for the LLM prompt:
  1. Deduplicate - drop exact-duplicate chunk_ids (can happen if a
     chunk was found by both semantic and keyword search - RRF already
     merges those into one entry, but this guards the general case of
     feeding in overlapping lists from elsewhere).
  2. Merge neighbors - if two surviving chunks are adjacent in the
     SAME source document (chunk_index differs by 1), concatenate
     their text into one combined block instead of sending two
     disconnected fragments - restores a coherent section.
  3. Restore document order - sort the (possibly merged) blocks by
     source_file then chunk_index, so the LLM reads chunks in the
     order they appear in the document, not RRF-rank order (rank
     order is for retrieval; document order is for reading).
  4. Token budget - trim to fit a total budget by dropping the
     lowest-relevance blocks first, keeping order intact for what
     remains.
  5. Citation tags - attach a stable [S1], [S2]... label per block, in
     final order, so the LLM (Stage 12) can cite which block it used.
"""

from chunker import count_tokens

DEFAULT_TOKEN_BUDGET = 4000


def _dedupe(chunks: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for c in chunks:
        if c["chunk_id"] in seen:
            continue
        seen.add(c["chunk_id"])
        result.append(c)
    return result


def _merge_adjacent(chunks: list[dict]) -> list[dict]:
    """Groups by source_file, sorts by chunk_index, merges runs of
    consecutive chunk_index into one block. Keeps the highest
    relevance score in the group (for token-budget trimming later)."""
    by_source: dict[str, list[dict]] = {}
    for c in chunks:
        by_source.setdefault(c["source_file"], []).append(c)

    merged = []
    for source_file, group in by_source.items():
        group.sort(key=lambda c: c["chunk_index"])
        run = [group[0]]
        for c in group[1:]:
            if c["chunk_index"] == run[-1]["chunk_index"] + 1:
                run.append(c)
            else:
                merged.append(_combine_run(run))
                run = [c]
        merged.append(_combine_run(run))
    return merged


def _combine_run(run: list[dict]) -> dict:
    if len(run) == 1:
        return {**run[0], "merged_from": [run[0]["chunk_index"]]}
    best = max(run, key=lambda c: c.get("rrf_score", c.get("similarity", 0)))
    combined_text = "\n\n".join(c["text"] for c in run)
    return {
        **best,
        "text": combined_text,
        # Re-tokenized from the actual combined text, not summed from
        # the source chunks' individual token_count fields - merging
        # isn't just concatenation-of-counts (tokenizer boundary
        # effects), and a stale/wrong count here would silently break
        # the token-budget step that runs right after this.
        "token_count": count_tokens(combined_text),
        "chunk_index": run[0]["chunk_index"],
        "page_number": sorted({p for c in run for p in (c.get("page_number") or [])}) or None,
        "merged_from": [c["chunk_index"] for c in run],
    }


def _restore_document_order(blocks: list[dict]) -> list[dict]:
    return sorted(blocks, key=lambda b: (b["source_file"], b["chunk_index"]))


def _apply_token_budget(blocks: list[dict], budget: int) -> tuple[list[dict], list[dict]]:
    """Drops lowest-relevance blocks first until total token_count fits
    the budget. Returns (kept, dropped), both still in document order."""
    ranked = sorted(
        blocks, key=lambda b: b.get("rrf_score", b.get("similarity", 0)), reverse=True
    )
    kept_ids = set()
    total = 0
    for b in ranked:
        tokens = b.get("token_count", 0)
        if total + tokens > budget and kept_ids:
            continue
        kept_ids.add(b["chunk_id"])
        total += tokens

    kept = [b for b in blocks if b["chunk_id"] in kept_ids]
    dropped = [b for b in blocks if b["chunk_id"] not in kept_ids]
    return kept, dropped


def build_context(chunks: list[dict], token_budget: int = DEFAULT_TOKEN_BUDGET) -> dict:
    """Runs the full Stage 11 pipeline. Returns a dict with the final
    citation-tagged blocks plus intermediate counts for eyeballing each
    step (dedup_count, merge_count, dropped_for_budget)."""
    deduped = _dedupe(chunks)
    merged = _merge_adjacent(deduped)
    ordered = _restore_document_order(merged)
    kept, dropped = _apply_token_budget(ordered, token_budget)

    tagged = []
    for i, block in enumerate(kept, start=1):
        tagged.append({**block, "citation_tag": f"S{i}"})

    return {
        "blocks": tagged,
        "dropped": dropped,
        "input_count": len(chunks),
        "after_dedup_count": len(deduped),
        "after_merge_count": len(merged),
        "final_count": len(tagged),
        "total_tokens": sum(b.get("token_count", 0) for b in tagged),
        "token_budget": token_budget,
    }
