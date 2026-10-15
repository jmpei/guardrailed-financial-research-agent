"""PageIndex document tools, plus a keyword search over page text: the agent decides which sections and pages to read."""
import json

from langchain_core.tools import BaseTool, StructuredTool
from pageindex import PageIndexClient

from gfra.config import DATA_DIR, MODEL

INDEX_DIR = DATA_DIR / "index"
SEARCH_MAX_PAGES = 10
SNIPPET_CHARS = 80


def make_client(model: str = MODEL) -> PageIndexClient:
    """Local-mode client: documents and trees stay on disk, model calls use OPENAI_API_KEY."""
    return PageIndexClient(index={"model": model, "storage_path": str(INDEX_DIR)}, chat=model)


def search_tool(client) -> BaseTool:
    def search_pages(doc_name: str, query: str) -> str:
        """Find the pages whose text contains a word or phrase (case-insensitive), with a snippet around the first match.

        Use it when the document structure does not show which pages hold what you need.

        Args:
            doc_name: Document name, e.g. "AMD_2022_10K.pdf".
            query: Word or phrase to find, e.g. "retention".
        """
        try:
            pages = client.get_ocr(client.get_document_id(doc_name), format="page")["result"]
        except Exception as exc:
            return json.dumps({"error": str(exc)})
        needle = query.lower()
        hits = []
        for page in pages:
            at = page["markdown"].lower().find(needle)
            if at >= 0:
                snippet = page["markdown"][max(0, at - SNIPPET_CHARS):at + len(query) + SNIPPET_CHARS]
                hits.append({"page": page["page_index"], "snippet": " ".join(snippet.split())})
        return json.dumps({"query": query, "pages_found": len(hits), "results": hits[:SEARCH_MAX_PAGES]}, ensure_ascii=False)

    return StructuredTool.from_function(search_pages, parse_docstring=False)


def document_tools(client) -> list[BaseTool]:
    return [StructuredTool.from_function(fn, parse_docstring=False) for fn in client.agent_tools()] + [search_tool(client)]
