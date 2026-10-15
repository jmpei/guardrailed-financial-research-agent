"""Citation check: is each number in an answer on the page the answer cites for it?

A number counts when it carries a $, a %, a scale word, a decimal point or thousands commas (bare
integers are mostly years, list items and product names). It is tied to the nearest page citation
after it on its line, else the nearest before it on its line, else the next citation in the answer,
else the last one. It is then looked up in the document's page text, the same text get_page_content
returns, allowing rounding and a "$2.2 billion" written as "2,182" in a table in millions:
- supported: on a cited page
- wrong_page: not on the cited pages but on another page of the document
- not_in_doc: on no page (a computed number, or an invented one)
- uncited: the answer cites no page at all
"""
import re
from collections import Counter

NUMBER = re.compile(r"(?<![\w.])(\$)?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(\s*%|\s*percent|\s+(?:thousand|million|billion))?",
                    re.IGNORECASE)
CITATION = re.compile(r"\bpages?\s+(\d+(?:\s*[-–]\s*\d+)?(?:\s*(?:,|and|&)\s*\d+(?:\s*[-–]\s*\d+)?)*)", re.IGNORECASE)
NOT_NUMBERS = re.compile(r"\S+\.pdf|\b10-[KQ]\b|^\s*\d+\.\s", re.IGNORECASE | re.MULTILINE)
SCALES = {"thousand": (1e3,), "million": (1e3, 1e6), "billion": (1e3, 1e6, 1e9)}
STATUSES = ("supported", "wrong_page", "not_in_doc", "uncited")


def _value(match: re.Match) -> float:
    return float(match.group(2).replace(",", "") + (match.group(3) or ""))


def _is_claim(match: re.Match) -> bool:
    return bool(match.group(1) or match.group(3) or match.group(4) or "," in match.group(2))


def _pages(spec: str) -> set[int]:
    pages = set()
    for part in re.split(r",|and|&", spec):
        bounds = [int(x) for x in re.findall(r"\d+", part)]
        if bounds:
            pages.update(range(bounds[0], bounds[-1] + 1))
    return pages


def _blank(match: re.Match) -> str:
    return " " * len(match.group(0))


def page_numbers(text: str) -> set[float]:
    return {_value(m) for m in NUMBER.finditer(text)}


def claims(answer: str) -> list[dict]:
    """The numbers in an answer, each with the pages it is cited to (empty when the answer cites none)."""
    lines = answer.splitlines()
    cites = [[(m.start(), _pages(m.group(1))) for m in CITATION.finditer(line)] for line in lines]
    out = []
    for i, line in enumerate(lines):
        masked = CITATION.sub(_blank, NOT_NUMBERS.sub(_blank, line))
        for m in NUMBER.finditer(masked):
            if not _is_claim(m):
                continue
            after = [p for start, p in cites[i] if start > m.start()]
            before = [p for start, p in cites[i] if start < m.start()]
            later = [p for line_cites in cites[i + 1:] for _, p in line_cites]
            earlier = [p for line_cites in cites[:i] for _, p in line_cites]
            pages = (after[:1] or before[-1:] or later[:1] or earlier[-1:] or [set()])[0]
            scale = (m.group(4) or "").strip().lower()
            out.append({"number": m.group(0).strip(), "value": _value(m), "decimals": len(m.group(3) or ".") - 1,
                        "scales": (1,) + SCALES.get(scale, ()), "cited": sorted(pages)})
    return out


def _on_page(claim: dict, values: set[float]) -> bool:
    return any(abs(round(v / s, claim["decimals"]) - claim["value"]) < 1e-9 for v in values for s in claim["scales"])


def check(answer: str, page_text: dict[int, str]) -> list[dict]:
    on_page = {page: page_numbers(text) for page, text in page_text.items()}
    results = []
    for c in claims(answer):
        found = sorted(page for page, values in on_page.items() if _on_page(c, values))
        if not c["cited"]:
            status = "uncited"
        elif set(found) & set(c["cited"]):
            status = "supported"
        elif found:
            status = "wrong_page"
        else:
            status = "not_in_doc"
        results.append({"number": c["number"], "cited": c["cited"], "found_on": found[:5], "status": status})
    return results


def summarize(checked: list[list[dict]]) -> dict:
    counts = Counter(r["status"] for answer in checked for r in answer)
    return {
        "answers": len(checked),
        "numbers": sum(counts.values()),
        **{status: counts[status] for status in STATUSES},
        "answers_with_wrong_page": sum(any(r["status"] == "wrong_page" for r in answer) for answer in checked),
    }
