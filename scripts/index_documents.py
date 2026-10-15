"""Build PageIndex trees for the FinanceBench filings. PAID: spends OpenAI tokens; quote and get approval first."""
import argparse
import sys
from pathlib import Path

from gfra.config import DATA_DIR, MODEL
from gfra.data import doc_names, load_questions
from gfra.retrieval import make_client


def pending_pdfs(client, names: list[str], pdf_dir: Path) -> list[Path]:
    """PDFs not yet in the store. Exits before any spend if a target PDF is missing."""
    missing = [n for n in names if not (pdf_dir / f"{n}.pdf").is_file()]
    if missing:
        sys.exit(f"Missing PDFs in {pdf_dir}: {', '.join(missing)}")
    stored = {d["name"] for d in client.list_documents(limit=10000)["documents"]}
    return [pdf_dir / f"{n}.pdf" for n in names if f"{n}.pdf" not in stored]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--docs", nargs="*", help="doc names to index; default: all 84")
    args = parser.parse_args()
    fb_dir = DATA_DIR / "financebench"
    names = args.docs or doc_names(load_questions(fb_dir / "financebench_open_source.jsonl"))
    client = make_client(args.model)
    for pdf in pending_pdfs(client, names, fb_dir / "pdfs"):
        print(pdf.stem, client.submit_document(str(pdf)))
    print(client.agent_tools()[0]())  # browse_documents: check the stored names match the doc names


if __name__ == "__main__":
    main()
