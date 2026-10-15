"""Check the page citations of a FinanceBench run against the indexed page text. Free: no API calls.

  uv run python scripts/check_citations.py runs/financebench/<run>.json

Prints one line per number that is not on its cited page, then the totals.
"""
import argparse
import json
from pathlib import Path

from gfra.citations import check, summarize
from gfra.config import DATA_DIR
from gfra.data import load_questions
from gfra.retrieval import make_client


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    docs = {q.id: q.doc_name for q in load_questions(DATA_DIR / "financebench" / "financebench_open_source.jsonl")}
    client = make_client()
    pages = {}
    checked = []
    for row in json.loads(args.run.read_text())["rows"]:
        doc = docs[row["id"]]
        if doc not in pages:
            ocr = client.get_ocr(client.get_document_id(f"{doc}.pdf"), format="page")["result"]
            pages[doc] = {p["page_index"]: p["markdown"] for p in ocr}
        results = check(row["answer"], pages[doc])
        checked.append(results)
        for r in results:
            if r["status"] != "supported":
                print(f"{row['id']}  trial {row['trial']}  {r['status']:10s}  {r['number']:>12s}  "
                      f"cited {r['cited'] or '-'}  found on {r['found_on'] or '-'}")
    print(json.dumps(summarize(checked), indent=2))


if __name__ == "__main__":
    main()
