import json
from dataclasses import dataclass
from pathlib import Path

BASE = "https://raw.githubusercontent.com/patronus-ai/financebench/main"
QUESTIONS_URL = f"{BASE}/data/financebench_open_source.jsonl"


@dataclass(frozen=True)
class Question:
    id: str
    doc_name: str
    question: str
    answer: str
    question_type: str


def load_questions(path: Path) -> list[Question]:
    questions = []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        questions.append(Question(
            id=row["financebench_id"],
            doc_name=row["doc_name"],
            question=row["question"],
            answer=row["answer"],
            question_type=row["question_type"],
        ))
    return questions


def doc_names(questions: list[Question]) -> list[str]:
    return sorted({q.doc_name for q in questions})


def pdf_url(doc_name: str) -> str:
    return f"{BASE}/pdfs/{doc_name}.pdf"
