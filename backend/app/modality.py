"""Requirement words (MUST, SHOULD, MAY...) must reach the answer exactly as the source has them.

Why: in standards, contracts and safety procedures "SHOULD NOT" and "MUST NOT" are different
obligations. The regression report (8 Oct 2026) caught the LLM paraphrasing an RFC's SHOULD and
SHOULD NOT as "must" and "must not", with the right citations, so it looked well supported.

The check: for each answer sentence, compare its requirement words with those in the sources it
cites. If the sentence says "must" (or "must not") and its sources only have the "should" family
for that polarity, it was strengthened; the reverse is weakening. "may" is left alone: in ordinary
prose ("you may find") it isn't a requirement.
"""

import re
from dataclasses import dataclass

# Longest phrases first, so "must not" isn't read as "must".
_TERMS = re.compile(
    r"\b(must not|mustn't|shall not|shan't|should not|shouldn't|not recommended|not required|"
    r"must|shall|required|should|recommended)\b", re.IGNORECASE)

# family, polarity
_CLASS = {
    "must": ("must", "+"), "shall": ("must", "+"), "required": ("must", "+"),
    "must not": ("must", "-"), "mustn't": ("must", "-"), "shall not": ("must", "-"), "shan't": ("must", "-"),
    "should": ("should", "+"), "recommended": ("should", "+"),
    "should not": ("should", "-"), "shouldn't": ("should", "-"), "not recommended": ("should", "-"),
    "not required": None,     # removes an obligation without forbidding anything: not compared
}

# What to write instead, keeping the source's capitals: (family, polarity) -> word
_WORD = {("must", "+"): "MUST", ("must", "-"): "MUST NOT", ("should", "+"): "SHOULD", ("should", "-"): "SHOULD NOT"}

_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")


def terms(text: str) -> list[tuple[str, tuple[str, str]]]:
    """[('SHOULD NOT', ('should', '-')), ...] in order of appearance."""
    return [(m.group(1), _CLASS[m.group(1).lower()]) for m in _TERMS.finditer(text)
            if _CLASS[m.group(1).lower()] is not None]


@dataclass
class Mismatch:
    sentence: str
    said: str            # the answer's word, e.g. "must not"
    source_says: str     # the cited sources' word for that polarity, e.g. "SHOULD NOT"
    sources: list[int]   # the [n] numbers the sentence cites


def _clauses(sentence: str) -> list[tuple[list[tuple[int, int]], list[int]]]:
    """Each requirement word is checked against the citation that follows it:
    'A must x [1], and B must not y [2].' -> clause 'A must x' with [1], ', and B must not y' with [2].
    Returns ([(start, end) spans of clause text], cited numbers); words after the last marker
    belong to the last clause."""
    pieces: list[tuple[list[tuple[int, int]], list[int]]] = []
    start = 0
    for marker in re.finditer(r"(?:\s*\[\d+(?:\s*,\s*\d+)*\])+", sentence):
        pieces.append(([(start, marker.start())], [int(n) for n in re.findall(r"\d+", marker.group(0))]))
        start = marker.end()
    if pieces and start < len(sentence):
        pieces[-1][0].append((start, len(sentence)))
    return pieces


def _text(sentence: str, spans: list[tuple[int, int]]) -> str:
    return " ".join(sentence[a:b] for a, b in spans)


def mismatches(answer: str, source_texts: list[str]) -> list[Mismatch]:
    """Sentences whose requirement word is stronger or weaker than every one in their sources.

    `source_texts[n - 1]` is the text of source [n]. Words without a citation aren't checked.
    """
    found: list[Mismatch] = []
    for sentence in _SENTENCE.split(answer):
        for spans, numbers in _clauses(sentence):
            clause = _text(sentence, spans)
            cited = sorted({n for n in numbers if 1 <= n <= len(source_texts)})
            in_sources = [cls for n in cited for _, cls in terms(source_texts[n - 1])]
            for word, (family, polarity) in terms(clause):
                same_polarity = {f for f, p in in_sources if p == polarity}
                if same_polarity and family not in same_polarity:
                    other = next(iter(same_polarity))
                    found.append(Mismatch(sentence.strip(), word, _WORD[(other, polarity)], cited))
    return found


def correction_note(found: list[Mismatch]) -> str:
    """The follow-up message asking the LLM to restore the sources' wording."""
    lines = [f'- "{m.sentence}" says "{m.said}", but source {", ".join(f"[{n}]" for n in m.sources)} '
             f'says "{m.source_says}".' for m in found]
    return ("Some requirement words in your answer are stronger or weaker than the sources:\n"
            + "\n".join(lines)
            + "\n\nRewrite the whole answer, keeping every requirement word (MUST, MUST NOT, SHOULD, "
              "SHOULD NOT, MAY) exactly as the source states it, in capitals. Keep the same citations.")


def restore(answer: str, source_texts: list[str]) -> str:
    """Last resort when the LLM's rewrite still has mismatches: swap the words in place,
    "must not" -> "SHOULD NOT" where the cited source says SHOULD NOT."""
    for _ in range(10):                       # one word per pass; sentences change as we go
        found = mismatches(answer, source_texts)
        if not found:
            break
        m = found[0]
        fixed = _swap_first(m, source_texts)
        answer = answer.replace(m.sentence, fixed, 1)
    return answer


def _swap_first(m: Mismatch, source_texts: list[str]) -> str:
    """The sentence with the mismatched word replaced, in the clause that cites m.sources."""
    word = re.compile(rf"\b{re.escape(m.said)}\b")
    for spans, numbers in _clauses(m.sentence):
        if sorted({n for n in numbers if 1 <= n <= len(source_texts)}) != m.sources:
            continue
        for a, b in spans:
            match = word.search(m.sentence, a, b)
            if match:
                return m.sentence[:match.start()] + m.source_says + m.sentence[match.end():]
    return word.sub(m.source_says, m.sentence, count=1)
