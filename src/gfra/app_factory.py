"""Wires the real model, PageIndex tools and actions together for the app, MCP server and evals."""
from langchain_openai import ChatOpenAI

from gfra.ablation import AGENTDOJO_PROMPT
from gfra.actions import fetch_news, send_email
from gfra.agent import Researcher
from gfra.config import MODEL
from gfra.observability import callbacks
from gfra.retrieval import document_tools, make_client

# With the attack on, the demo runs AgentDojo's no-defense baseline (its default system prompt, no defense lines):
# the setup the ablation measured the demo's attack on, 24 / 27 emails sent without Progent, 0 / 27 with it.
ATTACK_SETUP = {"system_prompt": AGENTDOJO_PROMPT, "prompt_defense": False}


def build_researcher(guarded: bool = True, model: str = MODEL, prompt_defense: bool = True,
                     system_prompt: str | None = None) -> Researcher:
    tools = [*document_tools(make_client()), fetch_news, send_email]
    llm = ChatOpenAI(model=model, temperature=0)
    return Researcher(llm, tools, guarded=guarded, callbacks=callbacks(), model_name=model,
                      prompt_defense=prompt_defense, system_prompt=system_prompt)
