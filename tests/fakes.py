"""A scripted chat model that returns the given messages in order, tool calls included."""
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage


class FakeToolModel(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def scripted(*messages):
    return FakeToolModel(messages=iter(messages))


def news_call(call_id):
    return AIMessage(content="", tool_calls=[{"name": "fetch_news", "args": {"company": "3M"}, "id": call_id}],
                     usage_metadata={"input_tokens": 100, "output_tokens": 10, "total_tokens": 110})


def email_call(to, call_id):
    return AIMessage(content="", tool_calls=[{"name": "send_email", "args": {"to": to, "subject": "s", "body": "b"}, "id": call_id}],
                     usage_metadata={"input_tokens": 100, "output_tokens": 10, "total_tokens": 110})
