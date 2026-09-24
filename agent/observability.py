"""Langfuse integration, isolated so the agent still answers questions even
if the observability backend is unreachable or misconfigured.

Every Langfuse call is wrapped so a failure only logs a warning - it never
takes down the agent's actual job of answering the question.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator, List, Optional, Tuple

from agent.config import Settings

logger = logging.getLogger(__name__)


class _NoOpSpan:
    """Used when tracing is disabled or unavailable, so callers don't need
    to branch on whether observability is on."""

    def update(self, **kwargs: Any) -> None:
        pass


class Observability:
    def __init__(self, settings: Settings):
        self.enabled = settings.langfuse_enabled
        self._client = None

        if self.enabled:
            try:
                from langfuse import get_client
                self._client = get_client()
            except Exception:
                logger.warning("Failed to initialize Langfuse client; tracing disabled", exc_info=True)
                self.enabled = False

    def callback_handler(self):
        if not self.enabled:
            return None
        try:
            from langfuse.langchain import CallbackHandler
            return CallbackHandler()
        except Exception:
            logger.warning("Failed to create Langfuse callback handler; tracing disabled", exc_info=True)
            return None

    @contextmanager
    def trace(self, name: str, input: Any = None) -> Iterator[Any]:
        if not self.enabled or self._client is None:
            yield _NoOpSpan()
            return
        try:
            with self._client.start_as_current_span(name=name, input=input) as span:
                yield span
        except Exception:
            logger.warning("Langfuse span '%s' failed; continuing without tracing", name, exc_info=True)
            yield _NoOpSpan()

    def tag_trace(self, *, user_id: str, session_id: str, tags: List[str]) -> None:
        if not self.enabled or self._client is None:
            return
        try:
            self._client.update_current_trace(user_id=user_id, session_id=session_id, tags=tags)
        except Exception:
            logger.warning("Failed to tag trace with session/user info", exc_info=True)

    def get_prompt(self, name: str, fallback_text: str) -> Tuple[str, Optional[Any]]:
        if not self.enabled or self._client is None:
            return fallback_text, None
        try:
            prompt = self._client.get_prompt(name)
            return prompt.compile(), prompt
        except Exception:
            logger.warning("Failed to fetch managed prompt '%s'; using fallback", name, exc_info=True)
            return fallback_text, None

    def score_trace(self, *, name: str, value: float, comment: str, data_type: str = "NUMERIC") -> None:
        if not self.enabled or self._client is None:
            return
        try:
            self._client.score_current_trace(name=name, value=value, data_type=data_type, comment=comment)
        except Exception:
            logger.warning("Failed to score trace with '%s'", name, exc_info=True)

    def current_trace_id(self) -> Optional[str]:
        if not self.enabled or self._client is None:
            return None
        try:
            return self._client.get_current_trace_id()
        except Exception:
            logger.warning("Failed to read current trace id", exc_info=True)
            return None

    def send_to_review_queue(self, trace_id: Optional[str], queue_name: str = "agent-review-queue") -> None:
        if not self.enabled or self._client is None or trace_id is None:
            return
        try:
            from langfuse.api.resources.annotation_queues.types.create_annotation_queue_item_request import (
                CreateAnnotationQueueItemRequest,
            )

            queues = {q.name: q for q in self._client.api.annotation_queues.list_queues(limit=100).data}
            queue = queues.get(queue_name)
            if queue is None:
                logger.warning("Annotation queue '%s' not found - run `python -m agent.setup_langfuse` first", queue_name)
                return
            self._client.api.annotation_queues.create_queue_item(
                queue.id,
                request=CreateAnnotationQueueItemRequest(object_id=trace_id, object_type="TRACE"),
            )
            logger.info("Trace %s sent to '%s' for human review", trace_id, queue_name)
        except Exception:
            logger.warning("Failed to push trace to review queue '%s'", queue_name, exc_info=True)

    def flush(self) -> None:
        if not self.enabled or self._client is None:
            return
        try:
            self._client.flush()
        except Exception:
            logger.warning("Failed to flush Langfuse events", exc_info=True)
