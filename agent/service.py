"""Shared "ask the agent a question" logic, used by both the CLI and the web UI."""
import logging
from dataclasses import dataclass, field
from typing import List, Tuple

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from agent.config import Settings
from agent.evaluation import evaluate_answer
from agent.graph import build_app
from agent.llm import get_llm
from agent.observability import Observability

logger = logging.getLogger(__name__)

FALLBACK_SYSTEM_PROMPT = "You are a helpful assistant that solves math and time questions."


@dataclass
class Step:
    node: str
    kind: str  # "tool_call" | "tool_result" | "answer"
    text: str


@dataclass
class AgentResult:
    steps: List[Step] = field(default_factory=list)
    final_answer: str = ""
    score: float = 0.0
    comment: str = ""
    error: str = ""


def ask(question: str, obs: Observability, cfg: Settings, source: str = "cli") -> AgentResult:
    app = build_app(get_llm(cfg))
    handler = obs.callback_handler()
    run_config = {"callbacks": [handler]} if handler else {}

    system_prompt, prompt_obj = obs.get_prompt("agent-answer-style", FALLBACK_SYSTEM_PROMPT)
    if prompt_obj is not None:
        run_config.setdefault("metadata", {})["langfuse_prompt"] = prompt_obj

    messages = [SystemMessage(system_prompt), HumanMessage(question)]
    result = AgentResult()
    # Langfuse renders this shape as a chat transcript on the trace.
    chat_input = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    with obs.trace(name="agent-run", input=chat_input) as span:
        obs.tag_trace(
            user_id=cfg.default_user_id,
            session_id=cfg.default_session_id,
            tags=[source],
            input=chat_input,
        )

        try:
            for step in app.stream({"messages": messages}, stream_mode="updates", config=run_config):
                for node, update in step.items():
                    for m in update["messages"]:
                        if getattr(m, "tool_calls", None):
                            call = m.tool_calls[0]
                            result.steps.append(Step(node, "tool_call", f"{call['name']}({call['args']})"))
                        elif isinstance(m, ToolMessage):
                            result.steps.append(Step(node, "tool_result", str(m.content)))
                        else:
                            result.steps.append(Step(node, "answer", m.content))
                            result.final_answer = m.content
        except Exception:
            logger.error("Agent run failed", exc_info=True)
            chat_output = [{"role": "assistant", "content": "Error: agent run failed"}]
            span.update(output=chat_output)
            obs.tag_trace(
                user_id=cfg.default_user_id,
                session_id=cfg.default_session_id,
                tags=[source],
                output=chat_output,
            )
            result.error = "The agent failed to produce an answer. Check server logs for details."
            obs.flush()
            return result

        chat_output = [{"role": "assistant", "content": result.final_answer}]
        span.update(output=chat_output)
        obs.tag_trace(
            user_id=cfg.default_user_id,
            session_id=cfg.default_session_id,
            tags=[source],
            output=chat_output,
        )
        result.score, result.comment = evaluate_answer(question, result.final_answer)
        obs.score_trace(name="correctness", value=result.score, comment=result.comment)

        if result.score == 0.0:
            obs.send_to_review_queue(obs.current_trace_id())

    obs.flush()
    return result
