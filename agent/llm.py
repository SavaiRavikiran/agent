"""LLM backend: real Claude when a key is configured, offline stub otherwise."""
import logging
import re

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from agent.config import Settings
from agent.tools import TOOLS

logger = logging.getLogger(__name__)

_MATH_PATTERN = re.compile(r"[\d(][\d\s+\-*/().]*[\d)]")


class OfflineLLM(BaseChatModel):
    """Deterministic rule-based stand-in so the graph runs without an API key."""

    @property
    def _llm_type(self) -> str:
        return "offline"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        last = messages[-1]
        if isinstance(last, ToolMessage):  # tool already ran -> give final answer
            msg = AIMessage(content=f"The answer is: {last.content}")
        else:
            text = last.content.lower()
            math = _MATH_PATTERN.search(text)
            if "time" in text or "date" in text:
                msg = AIMessage(content="", tool_calls=[
                    {"name": "current_time", "args": {}, "id": "call_1"}])
            elif math:
                msg = AIMessage(content="", tool_calls=[
                    {"name": "calculator", "args": {"expression": math.group()}, "id": "call_1"}])
            else:
                msg = AIMessage(content="I can do math or tell the time. Try: 'What is 12*7?'")
        return ChatResult(generations=[ChatGeneration(message=msg)])


def get_llm(settings: Settings) -> BaseChatModel:
    if settings.has_llm:
        from langchain_anthropic import ChatAnthropic
        logger.info("Using Claude (%s)", settings.anthropic_model)
        llm = ChatAnthropic(model=settings.anthropic_model, temperature=0)
    else:
        logger.warning("No ANTHROPIC_API_KEY configured - using offline fallback LLM")
        llm = OfflineLLM()
    return llm.bind_tools(TOOLS)
