"""LangGraph definition: LLM node + tool node in a ReAct loop.

    START -> agent --(tool call?)--> tools -> agent ... -> END
"""
from typing import Annotated, TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from agent.tools import TOOLS


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]  # appends, not overwrites


def build_app(llm: BaseChatModel):
    """Compile a fresh graph bound to the given (already tool-bound) LLM."""

    def agent_node(state: State):
        return {"messages": [llm.invoke(state["messages"])]}

    graph = StateGraph(State)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)  # -> "tools" or END
    graph.add_edge("tools", "agent")
    return graph.compile()
