"""CLI entrypoint: `python -m agent.cli "What is 23 * 47 + 10?"`"""
import sys

from agent.config import configure_logging, settings
from agent.observability import Observability
from agent.service import ask


def main(argv=None) -> int:
    configure_logging(settings.log_level)
    argv = sys.argv[1:] if argv is None else argv
    question = " ".join(argv) or "What is 23 * 47 + 10?"

    print(f"\nUser: {question}\n")
    obs = Observability(settings)
    result = ask(question, obs, settings, source="cli")

    if result.error:
        print(result.error)
        return 1

    for step in result.steps:
        if step.kind == "tool_call":
            print(f"[{step.node}] calls tool -> {step.text}")
        elif step.kind == "tool_result":
            print(f"[{step.node}] result  -> {step.text}")
        else:
            print(f"[{step.node}] answer  -> {step.text}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
