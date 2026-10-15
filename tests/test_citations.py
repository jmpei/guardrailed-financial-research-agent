from gfra.citations import check, claims, summarize

PAGES = {
    5: "billed business was $1,338 billion and we had 76.7 million proprietary cards-in-force",
    9: "To attract and retain talent we invest in colleague retention.",
    48: "Total provisions for credit losses $ 2,182 $ (1,419)",
    50: "Research and development expenses of $5.0 billion in 2022 increased by $2.2 billion, or 76%",
}


def statuses(answer: str) -> dict[str, str]:
    return {r["number"]: r["status"] for r in check(answer, PAGES)}


def test_number_on_the_cited_page_is_supported():
    assert statuses("R&D rose by 76% to $5.0 billion (AMD_2022_10K.pdf, page 50).") == {
        "76%": "supported", "$5.0 billion": "supported"}


def test_number_on_another_page_is_wrong_page():
    result = check("Billed business was $1,338 billion (Page 6).", PAGES)
    assert result == [{"number": "$1,338 billion", "cited": [6], "found_on": [5], "status": "wrong_page"}]


def test_number_on_no_page_is_not_in_doc():
    assert statuses("$1.5 billion 3.125% Senior Notes due 2025 (pages 12-14)") == {
        "$1.5 billion": "not_in_doc", "3.125%": "not_in_doc"}


def test_billions_match_a_table_in_millions():
    assert statuses("a reserve build of $2.2 billion against a release of $1.4 billion (page 48)") == {
        "$2.2 billion": "supported", "$1.4 billion": "supported"}


def test_percent_written_out_matches_the_sign():
    assert statuses("It rose 76 percent (page 50).") == {"76 percent": "supported"}


def test_a_later_citation_in_the_answer_covers_lines_without_one():
    answer = "1. Cards: 76.7 million in force.\n\nAll figures from AMERICANEXPRESS_2022_10K.pdf, pages 4-5."
    assert check(answer, PAGES)[0]["cited"] == [4, 5]


def test_answer_without_any_citation_is_uncited():
    assert statuses("Billed business was $1,338 billion.") == {"$1,338 billion": "uncited"}


def test_years_list_numbers_product_names_and_doc_names_are_not_claims():
    answer = "1. In 2022 the EPYC 9004 shipped (AMD_2022_10K.pdf, 10-K, page 7)."
    assert claims(answer) == []


def test_summarize_counts_answers_with_a_wrong_page():
    checked = [check("$1,338 billion (page 6)", PAGES), check("76% (page 50)", PAGES)]
    summary = summarize(checked)
    assert summary["wrong_page"] == 1 and summary["supported"] == 1
    assert summary["answers_with_wrong_page"] == 1
