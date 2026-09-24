"""CLI entrypoint: `python -m agent.cli "What is 23 * 47 + 10?"`"""
import logging
import sys

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from agent.config import Settings, configure_logging, settings
from agent.evaluation import evaluate_answer
from agent.graph import build_app
from agent.llm import get_llm
from agent.observability import Observability

logger = logging.getLogger(__name__)

FALLBACK_SYSTEM_PROMPT = "You are a helpful assistant that solves math and time questions."


def run(question: str, obs: Observability, cfg: Settings) -> int:
    app = build_app(get_llm(cfg))
    handler = obs.callback_handler()
    run_config = {"callbacks": [handler]} if handler else {}

    system_prompt, prompt_obj = obs.get_prompt("agent-answer-style", FALLBACK_SYSTEM_PROMPT)
    if prompt_obj is not None:
        run_config.setdefault("metadata", {})["langfuse_prompt"] = prompt_obj

    messages = [SystemMessage(system_prompt), HumanMessage(question)]

    with obs.trace(name="agent-run", input=question) as span:
        obs.tag_trace(user_id=cfg.default_user_id, session_id=cfg.default_session_id, tags=["cli"])

        final_answer = ""
        try:
            for step in app.stream({"messages": messages}, stream_mode="updates", config=run_config):
                for node, update in step.items():
                    for m in update["messages"]:
                        if getattr(m, "tool_calls", None):
                            call = m.tool_calls[0]
                            print(f"[{node}] calls tool -> {call['name']}({call['args']})")
                        elif isinstance(m, ToolMessage):
                            print(f"[{node}] result  -> {m.content}")
                        else:
                            print(f"[{node}] answer  -> {m.content}")
                            final_answer = m.content
        except Exception:
            logger.error("Agent run failed", exc_info=True)
            span.update(output="Error: agent run failed")
            return 1

        span.update(output=final_answer)
        score, comment = evaluate_answer(question, final_answer)
        obs.score_trace(name="correctness", value=score, comment=comment)

        if score == 0.0:
            obs.send_to_review_queue(obs.current_trace_id())

    obs.flush()
    return 0


def main(argv=None) -> int:
    configure_logging(settings.log_level)
    argv = sys.argv[1:] if argv is None else argv
    question = " ".join(argv) or "What is 23 * 47 + 10?"

    print(f"\nUser: {question}\n")
    obs = Observability(settings)
    return run(question, obs, settings)


if __name__ == "__main__":
    raise SystemExit(main())
