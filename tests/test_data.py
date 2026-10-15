import json
from gfra.data import load_questions, doc_names, pdf_url


def test_load_questions_and_doc_names(tmp_path):
    rows = [
        {"financebench_id": "fb_1", "doc_name": "3M_2018_10K", "question": "Capex?",
         "answer": "$1577.00", "question_type": "metrics-generated"},
        {"financebench_id": "fb_2", "doc_name": "AMD_2022_10K", "question": "Margin?",
         "answer": "44%", "question_type": "domain-relevant"},
        {"financebench_id": "fb_3", "doc_name": "3M_2018_10K", "question": "Debt?",
         "answer": "$13B", "question_type": "novel-generated"},
    ]
    path = tmp_path / "q.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows))
    qs = load_questions(path)
    assert [q.id for q in qs] == ["fb_1", "fb_2", "fb_3"]
    assert qs[0].answer == "$1577.00"
    assert doc_names(qs) == ["3M_2018_10K", "AMD_2022_10K"]


def test_pdf_url():
    assert pdf_url("3M_2018_10K") == (
        "https://raw.githubusercontent.com/patronus-ai/financebench/main/pdfs/3M_2018_10K.pdf"
    )
