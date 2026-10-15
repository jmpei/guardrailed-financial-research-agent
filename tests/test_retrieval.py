from gfra.retrieval import document_tools


class FakeClient:
    def agent_tools(self):
        def get_page_content(doc_name: str, pages: str) -> str:
            """Extract page content.

            Args:
                doc_name: Document name.
                pages: Page range like "5-7".
            """
            return f'{{"doc": "{doc_name}", "pages": "{pages}"}}'

        def browse_documents(offset: int = 0) -> str:
            """List documents."""
            return '{"documents": []}'

        return [get_page_content, browse_documents]


def test_document_tools_wraps_plain_functions_as_langchain_tools():
    tools = {t.name: t for t in document_tools(FakeClient())}
    assert set(tools) == {"get_page_content", "browse_documents"}
    out = tools["get_page_content"].invoke({"doc_name": "3M_2018_10K", "pages": "5-7"})
    assert '"pages": "5-7"' in out
    assert "doc_name" in tools["get_page_content"].args


def test_pending_pdfs_skips_stored_and_exits_on_missing(tmp_path):
    import importlib.util
    import pathlib

    import pytest

    spec = importlib.util.spec_from_file_location(
        "index_documents", pathlib.Path(__file__).parents[1] / "scripts" / "index_documents.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    class Store:
        def list_documents(self, limit):
            return {"documents": [{"name": "A.pdf"}]}

    for n in ("A", "B"):
        (tmp_path / f"{n}.pdf").write_bytes(b"")
    assert mod.pending_pdfs(Store(), ["A", "B"], tmp_path) == [tmp_path / "B.pdf"]
    with pytest.raises(SystemExit, match="C"):
        mod.pending_pdfs(Store(), ["A", "C"], tmp_path)
