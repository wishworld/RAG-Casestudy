"""Stage 6: query-time processing, starting with normalization.

Light normalization only - no LLM, no aggressive rewriting. Just
unicode/whitespace cleanup so "  AEPS   error 91 " and "AEPS error 91"
are treated identically downstream (embedding, keyword search, etc).
"""

import re
import unicodedata

# Unicode category "Cc" = control chars, "Cf" = format chars (includes
# invisible ones like zero-width space U+200B) - neither has a visible
# glyph, but both are real characters that can silently break exact-
# match comparisons and tokenization if pasted in from another app.
_CONTROL_OR_FORMAT_CATEGORIES = {"Cc", "Cf"}


def _strip_control_chars(text: str) -> str:
    return "".join(
        ch for ch in text
        if unicodedata.category(ch) not in _CONTROL_OR_FORMAT_CATEGORIES
        or ch in "\n\t"  # let whitespace cleanup handle these, not this step
    )


def normalize_query(query: str) -> str:
    normalized = unicodedata.normalize("NFKC", query)
    normalized = _strip_control_chars(normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized
