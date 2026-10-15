"""Download the FinanceBench open-source questions and the PDFs they use (free, no API key)."""
import urllib.request

from gfra.config import DATA_DIR
from gfra.data import QUESTIONS_URL, doc_names, load_questions, pdf_url


def main() -> None:
    fb_dir = DATA_DIR / "financebench"
    pdf_dir = fb_dir / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    questions_path = fb_dir / "financebench_open_source.jsonl"
    urllib.request.urlretrieve(QUESTIONS_URL, questions_path)
    names = doc_names(load_questions(questions_path))
    for name in names:
        target = pdf_dir / f"{name}.pdf"
        if not target.exists():
            urllib.request.urlretrieve(pdf_url(name), target)
    print(f"{len(names)} documents in {pdf_dir}")


if __name__ == "__main__":
    main()
