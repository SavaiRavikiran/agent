"""One-time setup: seeds the Langfuse project with the assets the agent and
experiment runner expect. Safe to re-run (idempotent).

    python -m agent.setup_langfuse

Creates:
  - Prompts          -> managed system prompt "agent-answer-style"
  - Datasets         -> "arithmetic-qa" with a few labeled Q/A items
  - Human Annotation -> a "correctness" score config + "agent-review-queue"
"""
import logging
import sys

from agent.config import configure_logging, settings

logger = logging.getLogger(__name__)

DATASET_NAME = "arithmetic-qa"
QA_ITEMS = [
    ("What is 23 * 47 + 10?", "1091"),
    ("What is 100 / 4 - 5?", "20"),
    ("What is 12 * 12?", "144"),
    ("What is 9 + 9 * 9?", "90"),
]


def main() -> int:
    configure_logging(settings.log_level)

    if not settings.langfuse_enabled:
        logger.error("LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY not set; nothing to set up")
        return 1

    from langfuse import get_client
    from langfuse.api.resources.annotation_queues.types.create_annotation_queue_request import (
        CreateAnnotationQueueRequest,
    )
    from langfuse.api.resources.score_configs.types.create_score_config_request import (
        CreateScoreConfigRequest,
    )

    langfuse = get_client()

    # ---------- Prompt Management (Prompts + Playground) ----------
    langfuse.create_prompt(
        name="agent-answer-style",
        prompt=(
            "You are a helpful assistant that solves math and time questions. "
            "Use the available tools when needed, and always end your reply with "
            "the final answer on its own line, e.g. 'Answer: 1091'."
        ),
        labels=["production"],
        type="text",
    )
    logger.info("prompt 'agent-answer-style' created/updated")

    # ---------- Datasets (backs Experiments) ----------
    try:
        langfuse.create_dataset(
            name=DATASET_NAME,
            description="Simple arithmetic questions with known answers, used by agent.experiment",
        )
        logger.info("dataset '%s' created", DATASET_NAME)
    except Exception as e:
        logger.info("dataset '%s' probably already exists (%s)", DATASET_NAME, e)

    existing_inputs = {item.input for item in langfuse.get_dataset(DATASET_NAME).items}
    added = 0
    for question, answer in QA_ITEMS:
        if question in existing_inputs:
            continue
        langfuse.create_dataset_item(dataset_name=DATASET_NAME, input=question, expected_output=answer)
        added += 1
    logger.info("dataset '%s' has %d seed items (%d newly added)", DATASET_NAME, len(QA_ITEMS), added)

    # ---------- Human Annotation (score config + review queue) ----------
    existing_configs = {c.name: c for c in langfuse.api.score_configs.get(limit=100).data}
    if "correctness" in existing_configs:
        score_config_id = existing_configs["correctness"].id
        logger.info("score config 'correctness' already exists")
    else:
        config = langfuse.api.score_configs.create(
            request=CreateScoreConfigRequest(
                name="correctness",
                data_type="NUMERIC",
                min_value=0,
                max_value=1,
                description="1 if the agent's final answer is arithmetically correct, else 0",
            )
        )
        score_config_id = config.id
        logger.info("score config 'correctness' created (%s)", score_config_id)

    existing_queues = {q.name: q for q in langfuse.api.annotation_queues.list_queues(limit=100).data}
    if "agent-review-queue" in existing_queues:
        logger.info("annotation queue 'agent-review-queue' already exists")
    else:
        queue = langfuse.api.annotation_queues.create_queue(
            request=CreateAnnotationQueueRequest(
                name="agent-review-queue",
                description="Traces where the automatic correctness score was 0 - needs human review",
                score_config_ids=[score_config_id],
            )
        )
        logger.info("annotation queue 'agent-review-queue' created (%s)", queue.id)

    langfuse.flush()
    logger.info("Done. Next: `python -m agent.cli \"...\"` or `python -m agent.experiment`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
