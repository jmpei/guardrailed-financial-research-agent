"""Wires the real model, PageIndex tools and actions together for the app, MCP server and evals."""
from langchain_openai import ChatOpenAI

from gfra.actions import fetch_news, send_email
from gfra.agent import Researcher
from gfra.config import MODEL
from gfra.observability import callbacks
from gfra.retrieval import document_tools, make_client


def build_researcher(guarded: bool = True, model: str = MODEL) -> Researcher:
    tools = [*document_tools(make_client()), fetch_news, send_email]
    llm = ChatOpenAI(model=model, temperature=0)
    return Researcher(llm, tools, guarded=guarded, callbacks=callbacks(), model_name=model)
