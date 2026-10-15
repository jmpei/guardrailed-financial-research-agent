"""PageIndex document tools: the agent decides which sections and pages to read."""
from langchain_core.tools import BaseTool, StructuredTool
from pageindex import PageIndexClient

from gfra.config import DATA_DIR, MODEL

INDEX_DIR = DATA_DIR / "index"


def make_client(model: str = MODEL) -> PageIndexClient:
    """Local-mode client: documents and trees stay on disk, model calls use OPENAI_API_KEY."""
    return PageIndexClient(index={"model": model, "storage_path": str(INDEX_DIR)}, chat=model)


def document_tools(client) -> list[BaseTool]:
    return [StructuredTool.from_function(fn, parse_docstring=False) for fn in client.agent_tools()]
