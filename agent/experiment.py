"""Runs the agent's graph against every item in the "arithmetic-qa" dataset
and records the results as a Langfuse Experiment.

Prerequisite: python -m agent.setup_langfuse   (creates the dataset)

Run:
    python -m agent.experiment
"""
import logging
import sys

from langchain_core.messages import HumanMessage, SystemMessage

from agent.config import configure_logging, settings
from agent.evaluation import evaluate_answer
from agent.graph import build_app
from agent.llm import get_llm

logger = logging.getLogger(__name__)

DATASET_NAME = "arithmetic-qa"
SYSTEM_PROMPT = "You are a helpful assistant that solves math and time questions."


def make_task(app):
    def task(*, item, **kwargs):
        """run_experiment() already wraps this call in its own traced span and
        links it to the dataset run - no manual span handling needed here."""
        messages = [SystemMessage(SYSTEM_PROMPT), HumanMessage(item.input)]
        final_answer = ""
        for step in app.stream({"messages": messages}, stream_mode="updates"):
            for _node, update in step.items():
                for m in update["messages"]:
                    if not getattr(m, "tool_calls", None):
                        final_answer = m.content
        return final_answer

    return task


def correctness_evaluator(*, input, output, expected_output, metadata, **kwargs):
    from langfuse.experiment import Evaluation

    score, comment = evaluate_answer(input, output or "")
    return Evaluation(name="correctness", value=score, comment=comment)


def main() -> int:
    configure_logging(settings.log_level)

    if not settings.langfuse_enabled:
        logger.error("LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY not set; cannot run experiment")
        return 1

    from langfuse import get_client

    langfuse = get_client()
    dataset = langfuse.get_dataset(DATASET_NAME)
    app = build_app(get_llm(settings))

    result = langfuse.run_experiment(
        name="arithmetic-qa-eval",
        description="Runs the agent against the arithmetic-qa dataset and scores correctness",
        data=dataset.items,
        task=make_task(app),
        evaluators=[correctness_evaluator],
    )
    langfuse.flush()

    total = len(result.item_results)
    correct = sum(
        1
        for r in result.item_results
        for e in r.evaluations
        if e.name == "correctness" and e.value == 1.0
    )
    logger.info("Experiment '%s' done: %d/%d correct.", result.name, correct, total)
    logger.info("See Datasets -> %s -> Runs, and Evaluation -> Experiments in Langfuse.", DATASET_NAME)
    return 0


if __name__ == "__main__":
    sys.exit(main())
