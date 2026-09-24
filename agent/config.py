"""Centralized configuration and logging setup.

All environment-driven behavior for the agent goes through Settings so there
is a single, typed source of truth instead of scattered os.getenv() calls.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: Optional[str]
    anthropic_model: str
    langfuse_public_key: Optional[str]
    langfuse_secret_key: Optional[str]
    langfuse_host: Optional[str]
    default_user_id: str
    default_session_id: str
    log_level: str

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)

    @property
    def has_llm(self) -> bool:
        return bool(self.anthropic_api_key)

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"),
            langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY") or None,
            langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY") or None,
            langfuse_host=os.getenv("LANGFUSE_HOST") or None,
            default_user_id=os.getenv("DEMO_USER_ID", "cli-user"),
            default_session_id=os.getenv("DEMO_SESSION_ID", "cli-demo-session"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Quiet noisy third-party loggers unless we're explicitly at DEBUG.
    if level != "DEBUG":
        for noisy in ("httpx", "httpcore", "urllib3"):
            logging.getLogger(noisy).setLevel(logging.WARNING)


settings = Settings.from_env()
