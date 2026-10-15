"""Build PageIndex trees for the FinanceBench filings. PAID: spends OpenAI tokens; quote and get approval first."""
import argparse

from gfra.config import DATA_DIR, MODEL
from gfra.data import doc_names, load_questions
from gfra.retrieval import make_client


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--docs", nargs="*", help="doc names to index; default: all 84")
    args = parser.parse_args()
    fb_dir = DATA_DIR / "financebench"
    names = args.docs or doc_names(load_questions(fb_dir / "financebench_open_source.jsonl"))
    client = make_client(args.model)
    for name in names:
        result = client.submit_document(str(fb_dir / "pdfs" / f"{name}.pdf"))
        print(name, result)
    print(client.agent_tools()[0]())  # browse_documents: check the stored names match the doc names


if __name__ == "__main__":
    main()
