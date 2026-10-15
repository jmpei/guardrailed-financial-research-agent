"""Progent privilege control as a LangChain agent middleware.

Before each task, Progent's policy model writes a policy from the user's request. Before each
tool call, Progent's deterministic checker compares the call with the policy. Read-only tools
are always allowed; tools with side effects run only if the policy allows the exact arguments.
"""
import os

from gfra.config import MODEL, READ_ONLY_TOOLS

# secagent reads these once, at import time.
os.environ.setdefault("SECAGENT_POLICY_MODEL", MODEL)
os.environ.setdefault("SECAGENT_GENERATE", "True")
os.environ.setdefault("SECAGENT_UPDATE", "True")
os.environ.setdefault("SECAGENT_IGNORE_UPDATE_ERROR", "True")

import secagent.tool as st  # noqa: E402
from langchain.agents.middleware import AgentMiddleware  # noqa: E402
from langchain_core.messages import ToolMessage  # noqa: E402
from langchain_core.tools import BaseTool  # noqa: E402
from openai import OpenAI  # noqa: E402

_usage = {"input": 0, "output": 0}


def _policy_request(sys_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
    """Same request as secagent's default OpenAI branch, plus token counting."""
    completion = OpenAI().chat.completions.create(
        messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}],
        model=st.policy_model,
        temperature=temperature,
        seed=0,
    )
    _usage["input"] += completion.usage.prompt_tokens
    _usage["output"] += completion.usage.completion_tokens
    return completion.choices[0].message.content


# Route every secagent policy call through _policy_request (looked up at call time, so tests can patch it).
st.api_request = lambda sys_prompt, user_prompt, temperature=0.0: _policy_request(sys_prompt, user_prompt, temperature)


class Guard:
    def __init__(self, tools: list[BaseTool]):
        self.tool_names = [t.name for t in tools]
        st.update_available_tools([])
        st.add_langchain_tools(tools)
        self.blocked: list[dict] = []
        self.policy_tokens = _usage

    def start_task(self, query: str) -> None:
        """Forget the previous task's policy, then write a new one for this query (fails closed)."""
        self.blocked = []
        _usage["input"] = _usage["output"] = 0
        st.reset_security_policy(include_human_policy=True)
        st.update_always_allowed_tools([n for n in self.tool_names if n in READ_ONLY_TOOLS])
        try:
            st.generate_security_policy(query)
        except Exception:
            # Drop any rules a failed attempt left behind: side-effect tools then match no rule and are blocked.
            st.reset_security_policy()

    def middleware(self) -> AgentMiddleware:
        guard = self

        class _GuardMiddleware(AgentMiddleware):
            async def awrap_tool_call(self, request, handler):
                name, args = request.tool_call["name"], request.tool_call["args"]
                try:
                    st.check_tool_call(name, args)
                except st.ValidationError as exc:
                    guard.blocked.append({"tool": name, "args": args, "reason": str(exc)})
                    return ToolMessage(content=f"Blocked by guardrail: {exc}", tool_call_id=request.tool_call["id"])
                result = await handler(request)
                try:
                    st.generate_update_security_policy([{"name": name, "args": args}], str(result.content), manual_check=False)
                except Exception:
                    pass  # update failed: keep the current policy
                return result

        return _GuardMiddleware()
