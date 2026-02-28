"""LLM Factory with logging and token tracking.

This module provides:
- Cached LLM instance creation
- Token usage tracking
- LLM call logging with request correlation
- Cost tracking integration with CostService
"""

import time
from functools import lru_cache
from typing import Optional

from langchain_community.cache import InMemoryCache
from langchain_core.globals import set_llm_cache
from langchain_openai import ChatOpenAI

from app.config.settings import get_settings
from app.core.logging import get_logger

set_llm_cache(InMemoryCache())

logger = get_logger(__name__)

# Thread-local storage for session ID
import threading

_session_context = threading.local()


def set_session_id(session_id: str) -> None:
    """Set the session ID for the current context.

    Args:
        session_id: The session identifier to associate with LLM calls
    """
    _session_context.session_id = session_id


def get_session_id() -> Optional[str]:
    """Get the session ID for the current context.

    Returns:
        The current session ID or None if not set
    """
    return getattr(_session_context, "session_id", None)


def clear_session_id() -> None:
    """Clear the session ID from the current context."""
    if hasattr(_session_context, "session_id"):
        delattr(_session_context, "session_id")


class TokenTracker:
    """Track LLM token usage across calls.

    This class provides a singleton-like tracking mechanism for
    aggregating token usage statistics.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.call_count: int = 0

    def add_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Add token usage to the tracker.

        Args:
            input_tokens: Number of input/prompt tokens
            output_tokens: Number of output/completion tokens
        """
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.call_count += 1

    def get_summary(self) -> dict:
        """Get a summary of token usage.

        Returns:
            Dictionary with total_input_tokens, total_output_tokens,
            total_tokens, and call_count
        """
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "call_count": self.call_count,
        }

    def reset(self) -> None:
        """Reset all counters to zero."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.call_count = 0


# Global token tracker instance
_token_tracker: TokenTracker | None = None


def get_token_tracker() -> TokenTracker:
    """Get the global token tracker instance.

    Returns:
        The singleton TokenTracker instance
    """
    global _token_tracker
    if _token_tracker is None:
        _token_tracker = TokenTracker()
    return _token_tracker


def log_llm_call(
    model: str,
    input_tokens: int,
    output_tokens: int,
    duration_ms: int,
    session_id: Optional[str] = None,
) -> None:
    """Log an LLM call with token usage and timing.

    Args:
        model: The model name used
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        duration_ms: Duration of the call in milliseconds
        session_id: Optional session ID for cost tracking
    """
    logger.info(
        "llm_call",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        duration_ms=duration_ms,
    )

    # Track token usage
    tracker = get_token_tracker()
    tracker.add_usage(input_tokens, output_tokens)

    # Record cost in CostService if session_id is available
    effective_session_id = session_id or get_session_id()
    if effective_session_id and input_tokens > 0:
        try:
            from app.services.cost_service import CostService

            cost_service = CostService.get_instance()
            cost_service.record_usage(
                session_id=effective_session_id,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        except Exception as e:
            logger.warning(
                "Failed to record cost",
                session_id=effective_session_id,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )


def create_tracked_llm(
    model: str,
    api_key: str,
    temperature: float = 0.0,
    streaming: bool = False,
) -> ChatOpenAI:
    """Create an LLM instance with call tracking.

    Args:
        model: The model name
        api_key: OpenAI API key
        temperature: Temperature setting
        streaming: Whether to enable streaming

    Returns:
        A ChatOpenAI instance with tracking callbacks
    """
    from langchain_core.callbacks import BaseCallbackHandler

    class TracingCallbackHandler(BaseCallbackHandler):
        """Callback handler for tracing LLM calls."""

        def __init__(self):
            super().__init__()
            self._start_time: float | None = None
            self._model_name: str = model

        def on_llm_start(self, serialized, prompts, **kwargs):
            """Record the start time of LLM call."""
            self._start_time = time.time()

        def on_llm_end(self, response, **kwargs):
            """Log the LLM call with token usage."""
            if self._start_time is None:
                return

            duration_ms = int((time.time() - self._start_time) * 1000)

            # Extract token usage from response
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, "llm_output") and response.llm_output:
                token_usage = response.llm_output.get("token_usage", {})
                input_tokens = token_usage.get("prompt_tokens", 0)
                output_tokens = token_usage.get("completion_tokens", 0)

            log_llm_call(
                model=self._model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
            )

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        temperature=temperature,
        streaming=streaming,
        callbacks=[TracingCallbackHandler()],
    )


@lru_cache(maxsize=8)
def get_llm(temperature: float = 0.0, streaming: bool = False) -> ChatOpenAI:
    """LLM インスタンスをキャッシュして返す。

    同一パラメータでの呼び出しは同じインスタンスを返す。
    """
    settings = get_settings()
    return create_tracked_llm(
        model=settings.openai_model,
        api_key=settings.openai_api_key.get_secret_value(),
        temperature=temperature,
        streaming=streaming,
    )
