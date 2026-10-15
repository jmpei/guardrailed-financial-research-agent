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
