"""Query processing: read filters out of the question before searching.

Right now: a year. "Why did revenue decline in 2024?" -> only consider 2024 documents
(plus undated ones). This is the "Query processing / extract filters" box in the diagram.
"""

import re
from dataclasses import dataclass

# A year only counts when a time word comes right before it: "in 2024", "since 2019",
# "FY2024", "year 2023". That keeps "more than 2000 dimensions" or "port 2020" from
# being mistaken for a year. A missed filter is harmless; a wrong one hides documents.
_YEAR = re.compile(
    r"\b(?:in|during|since|from|for|of|by|before|after|until|year|fy)\s*'?(19[5-9]\d|20\d{2})\b",
    re.IGNORECASE,
)


@dataclass
class ParsedQuery:
    text: str                  # what we search for (unchanged: the year helps keyword search too)
    year: int | None = None

    @property
    def filters(self) -> dict:
        """The filters that were applied, for showing to the user."""
        return {"year": self.year} if self.year is not None else {}


def parse_query(question: str) -> ParsedQuery:
    years = {int(match) for match in _YEAR.findall(question)}
    # "Compare 2023 and 2024" mentions two years: that's a comparison, not a filter.
    year = years.pop() if len(years) == 1 else None
    return ParsedQuery(text=question.strip(), year=year)
