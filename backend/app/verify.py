"""Citation check: the figures and codes in an answer must be in the sources it cites.

Why: a citation makes a sentence look supported. The 8 Oct 2026 runs had answers citing the right
passage while getting its numbers wrong (512 units where the rows add up to 464), and answers
whose figure was in a different source than the one cited. Wrong numbers, dates and codes are
the errors that matter most and the easiest to check without another model: they either appear
in a source or they don't.

For each clause with a citation, every "fact" (a token with a digit: 464, 05:55, 4.9,
2026-10-01, TG-203, MR-AIR-518) is looked up in the cited sources. One that isn't there but is
in another source gets that source's citation added. One that is in no source at all is
unsupported: the model gets one chance to correct it (see generate.generate_answer), and
whatever is still unsupported is reported with the answer, so the reader knows to check it.

Small integers (counts like "4 items", list numbers) and figures repeated from the question are
not checked, and neither are results the sentence shows how to get: "360 of the 1,200 hours, which
is 30 %", "640 m³ × 50 % = 320 m³", "launched at 06:00 and 18:00, 12 hours apart", or a total
after "48 + 35 + 64 = 147".
"""

import re

from app.modality import _clauses

_FACT = re.compile(r"(?<![\w.])(?:[A-Za-z]+[-_])*[A-Za-z]*\d[\w:./-]*")
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
SMALL = 10                     # integers up to this are usually counts, not figures from a source


def _plain(text: str) -> str:
    """Same spelling for both sides: 1,064 -> 1064, 05:55 -> 5:55, lower case."""
    text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)
    return re.sub(r"(?<![\d:])0(\d:\d\d)", r"\1", text).lower()


def facts(text: str) -> list[str]:
    """The checkable tokens of a text, normalised: 'TG-203 has 1,064 units [2].' -> ['tg-203', '1064']"""
    text = _plain(re.sub(r"\[\d+(?:\s*,\s*\d+)*\]", " ", text))     # citation markers aren't facts
    found = []
    for match in _FACT.finditer(text):
        token = match.group(0).rstrip(".:/-")
        if (re.fullmatch(r"\d+", token) and int(token) <= SMALL) or re.fullmatch(r"\d+(?:st|nd|rd|th)", token):
            continue                           # a count or an ordinal ("4 items", "2nd")
        if token:
            found.append(token)
    return list(dict.fromkeys(found))


def _numbers(text: str) -> list[float]:
    """Every number in a text, times as hours: '06:00 and 18:30' -> [6.0, 18.5]."""
    text = re.sub(r"\[\d+(?:\s*,\s*\d+)*\]", " ", _plain(text))
    out = [int(h) + int(m) / 60 for h, m in re.findall(r"\b(\d{1,2}):(\d\d)\b", text)]
    text = re.sub(r"\b\d{1,2}:\d\d\b", " ", text)
    return out + [float(n) for n in re.findall(r"(?<![\w.-])\d+(?:\.\d+)?", text)]


def _calculated(fact: str, sentence: str) -> bool:
    """Whether a number is one calculation away from the other numbers in its sentence, or the
    total of a sum written out in it."""
    if not re.fullmatch(r"\d+(?:\.\d+)?", fact):
        return False
    value = float(fact)
    places = len(fact.split(".")[1]) if "." in fact else 0
    plain = _plain(sentence)
    for terms in re.findall(rf"((?:\d+(?:\.\d+)?\s*\+\s*)+\d+(?:\.\d+)?)\s*=\s*{re.escape(fact)}\b", plain):
        if round(sum(float(t) for t in terms.split("+")), places) == value:
            return True                        # "48 + 35 + 64 = 147"
    others = _numbers(sentence)
    if value in others:
        others.remove(value)
    for i, a in enumerate(others):
        for b in others[i + 1:]:
            results = [a + b, abs(a - b), a * b, a * b / 100]
            if a and b:
                results += [a / b, b / a, a / b * 100, b / a * 100]
            if any(round(x, places) == value for x in results):
                return True
    return False


def _in(fact: str, source_facts: set[str], source_text: str) -> bool:
    if fact in source_facts:
        return True
    # "2026" inside "2026-10-01", "47" inside "47-minute": a whole part of a longer token.
    return bool(re.search(rf"(?<![\w.]){re.escape(fact)}(?![\w]|\.\d)", source_text))


class _Sources:
    def __init__(self, texts: list[str]):
        self.texts = [_plain(t) for t in texts]
        self.facts = [set(facts(t)) for t in texts]

    def having(self, fact: str) -> list[int]:
        """1-based numbers of the sources containing the fact."""
        return [n for n, (f, t) in enumerate(zip(self.facts, self.texts), start=1) if _in(fact, f, t)]


def recite(answer: str, source_texts: list[str], question: str = "") -> tuple[str, list[str]]:
    """Add the right citation where a clause's figure is only in another source, and list the
    figures that are in no source at all. Returns (answer, unsupported facts)."""
    sources = _Sources(source_texts)
    asked = set(facts(question))
    unsupported: list[str] = []
    out_lines = []
    for line in answer.split("\n"):
        out_sentences = []
        for sentence in re.split(r"(?<=[.!?])(\s+)", line):
            if not sentence.strip():
                out_sentences.append(sentence)
                continue
            out_sentences.append(_recite_sentence(sentence, sources, asked, unsupported))
        out_lines.append("".join(out_sentences))
    return "\n".join(out_lines), list(dict.fromkeys(unsupported))


def _recite_sentence(sentence: str, sources: _Sources, asked: set[str], unsupported: list[str]) -> str:
    clauses = _clauses(sentence)
    if not clauses:                            # no citation: only check the facts exist somewhere
        unsupported += [f for f in facts(sentence) if f not in asked and not sources.having(f)
                        and not _calculated(f, sentence)]
        return sentence
    additions: dict[int, list[int]] = {}       # clause index -> source numbers to add
    for i, (spans, numbers) in enumerate(clauses):
        clause = " ".join(sentence[a:b] for a, b in spans)
        cited = [n for n in numbers if 1 <= n <= len(sources.texts)]
        for fact in facts(clause):
            if fact in asked:
                continue
            where = sources.having(fact)
            if not where:
                if not _calculated(fact, sentence):
                    unsupported.append(fact)
            elif not set(where) & set(cited) and len(where) == 1:
                additions.setdefault(i, []).append(where[0])
    if not additions:
        return sentence
    # Insert the added markers right after each clause's existing citation group.
    markers = list(re.finditer(r"(?:\s*\[\d+(?:\s*,\s*\d+)*\])+", sentence))
    for i in sorted(additions, reverse=True):
        end = markers[i].end()
        extra = "".join(f"[{n}]" for n in dict.fromkeys(additions[i]))
        sentence = sentence[:end] + extra + sentence[end:]
    return sentence


def correction_note(unsupported: list[str]) -> str:
    """The follow-up asking the LLM to fix figures no source contains."""
    listed = ", ".join(f'"{f}"' for f in unsupported)
    return (f"These figures or codes in your answer don't appear in any of the sources: {listed}. "
            "Rewrite the whole answer, using only values that appear in the sources (copy them exactly). "
            "If a value has to be calculated, use the computed figures a source gives, or show the "
            "calculation from source values. Keep the same citations.")
