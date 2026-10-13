"""Compound questions: split a question into the parts ("facets") that each need their own source.

Why: one search for "During a conservation order, the back-pump fails and an amber alert is raised
while a barge is in the chamber. What should the keeper do?" finds the passages closest to the
question *as a whole*. Sections that match only one part (the amber-alert rule) score low against
the full question and get cut, so the answer wrongly says the document doesn't cover them. Here
each part is searched on its own, and the best passage for every part is kept.

Splitting is rule-based (no extra LLM call): at sentence ends, semicolons, commas and joining
words like "and", "while", "but". Parts with fewer than two content words ("It is Monday") are
not searched alone; they stay in the full-question search. Neither are instructions about the
answer itself ("Preserve accented characters", "Show the arithmetic"): there is nothing to find
for them, and searching them only made the answer report them as "not covered".
"""

import re

MAX_FACETS = 8   # a part beyond this is still in the full-question search, but gets no search of its own
MIN_CONTENT_WORDS = 2

# Words that carry no topic of their own: question words, auxiliaries, articles, pronouns...
_FILLER = set("""
a an the and or but nor so yet if when while whereas then also plus as of to in on at by for from with
without into onto about between within through during before after since until than that this these
those it its is are was were be been being am do does did done has have had having can could should
would will shall may might must not no yes any all each every some what which who whom whose why how
where there here i me my we our you your he she they them their his her one ones please tell give
show list describe explain say says said what's whats there's get gets got also both either neither
many much
""".split())

# What kind of answer is wanted, not what it's about: "What exact ordered actions are required?"
# has no topic to search for, and reporting it as "not covered" made answers decline parts they
# had answered. (Topics keep these words when they have another: "required access token".)
_FILLER |= set("""
action actions step steps sequence ordered exact exactly required require requires requirement
compare comparison detail details information complete full entire
""".split())

# Where one part ends and the next begins.
_SPLIT = re.compile(
    r"[.?!;]\s+|,\s*(?:and|or|but|while|then|plus)?\s*|\s+(?:and|while|whereas|but|then|plus|as well as|"
    r"and also|also)\s+",
    re.IGNORECASE)

_SPLIT_KEEP = re.compile(f"({_SPLIT.pattern})", re.IGNORECASE)
_WORD_JOIN = re.compile(r"\s+(?:and|or)\s+", re.IGNORECASE)
# "Answer: how long...": a label, not part of what to search for.
_ANSWER_LABEL = re.compile(r"^(?:answer|question|q)\s*\d*\s*:\s*", re.IGNORECASE)
# Where a part's answer should come from, not a part of its own.
_ATTRIBUTION = re.compile(r"^(?:according to|as (?:stated|described|given) (?:in|by)|per|from)\s", re.IGNORECASE)

# A part that tells the model how to answer rather than asking about the documents.
_INSTRUCTION = re.compile(
    r"^(?:please\s+)?(?:(?:using|use|from|across|with) (?:all|both|each|every|the) (?:\w+ )?(?:sources?|documents?|files?)\b|"
    r"preserve|keep|format|respond|reply|cite|quote|write|be|combine|answer (?:in|with|briefly)|"
    r"show (?:the |your |all )?(?:work|working|arithmetic|calculations?|steps|sums|totals))\b", re.IGNORECASE)


def content_words(text: str) -> list[str]:
    return [w for w in re.findall(r"[\w.%-]+", text.lower()) if len(w) >= 3 and w not in _FILLER]


def split_facets(question: str) -> list[str]:
    """The independently searchable parts of a question; [] when it has only one part.

    "What is the daily schedule, and what is on the opening checklist?"
        -> ["What is the daily schedule", "what is on the opening checklist"]
    """
    pieces = _SPLIT_KEEP.split(question)            # [text, separator, text, separator, ..., text]
    parts: list[str] = []
    carried = ""
    for i in range(0, len(pieces), 2):
        text, sep = carried + pieces[i], pieces[i + 1] if i + 1 < len(pieces) else ""
        carried = ""
        if 0 < len(content_words(text)) < MIN_CONTENT_WORDS and _WORD_JOIN.fullmatch(sep):
            # "Which team and count belong to Blue Heron": "and" joined two words, not two parts.
            # Splitting there dropped "Which team" and searched only "count belong to Blue Heron".
            carried = text + sep
            continue
        text = _ANSWER_LABEL.sub("", text.strip(" ,.;:?!"))
        if parts and _ATTRIBUTION.match(text):
            parts[-1] += f", {text}"                 # "..., according to IANA" belongs to the part before
            continue
        parts.append(text)
    parts = [p for p in parts if len(content_words(p)) >= MIN_CONTENT_WORDS and not _INSTRUCTION.match(p)]
    # Drop repeats ("What should X do" twice) but keep the order.
    unique: list[str] = []
    for part in parts:
        if not any(content_words(part) == content_words(u) for u in unique):
            unique.append(part)
    return unique[:MAX_FACETS] if len(unique) >= 2 else []


# Capitalised words that aren't the first word of a sentence: names ("Sable Ridge", "Vesper").
_NAME = re.compile(r"(?<![.?!:]\s)(?<!^)\b[A-Z][\w'’-]*(?:\s+[A-Z][\w'’-]*)*")


def names(question: str) -> list[str]:
    """The names a question is about, in order: "...the Sable Ridge departure checklist, and state
    when the Vesper departs" -> ["Sable Ridge", "Vesper"]."""
    found = [re.sub(r"['’]s$", "", n) for n in _NAME.findall(question.strip())]
    return list(dict.fromkeys(n for n in found if n.lower() not in _FILLER))


def with_context(facet: str, question: str) -> str:
    """A facet to search on its own, with the names it lost in the split.

    "its travel time" means nothing without "the Vesper": the reranker scored the passage saying
    the Vesper "reaches Summit Gate after 47 minutes" 0.0001 for it, so the answer was told the
    travel time wasn't covered. "its travel time (Sable Ridge, Vesper)" scores it 0.997.
    A facet that already names something keeps its own wording.
    """
    lost = names(question)
    if not lost or any(n.lower() in facet.lower() for n in lost):
        return facet
    return f"{facet} ({', '.join(lost)})"

