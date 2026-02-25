"""Cost Service for tracking LLM token usage and costs.

This module provides:
- Token usage recording per session
- Cost calculation by model
- Session-based cost aggregation
- Cost limit checking
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

# Model pricing (USD per 1M tokens)
MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}

# Default pricing for unknown models (same as gpt-4o-mini)
DEFAULT_PRICING = {"input": 0.15, "output": 0.60}


@dataclass
class TokenUsage:
    """Represents a single token usage record."""

    timestamp: str
    session_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class CostService:
    """Service for tracking and aggregating LLM costs.

    Implements singleton pattern for global cost tracking.
    Supports persistence to JSON file.
    """

    _instance = None
    _lock = Lock()

    def __new__(cls, persist_path: str = "data/token_usage.json"):
        """Create or return the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._usages: list[TokenUsage] = []
                    instance._persist_path = Path(persist_path)
                    instance._load()
                    cls._instance = instance
        return cls._instance

    def __init__(self, persist_path: str = "data/token_usage.json"):
        """Initialize the CostService.

        Args:
            persist_path: Path to the JSON file for persistence
        """
        # Initialization is done in __new__ for singleton pattern
        pass

    @classmethod
    def get_instance(cls) -> "CostService":
        """Get the singleton instance of CostService."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (for testing)."""
        cls._instance = None

    def _get_pricing(self, model: str) -> dict:
        """Get pricing for a model.

        Args:
            model: The model name

        Returns:
            Dictionary with 'input' and 'output' prices per 1M tokens
        """
        # Normalize model name (handle variations)
        model_lower = model.lower()

        # Direct match
        if model_lower in MODEL_PRICING:
            return MODEL_PRICING[model_lower]

        # Partial match (e.g., "gpt-4o-mini-2024-07-18")
        for key in MODEL_PRICING:
            if key in model_lower:
                return MODEL_PRICING[key]

        return DEFAULT_PRICING

    def _calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Calculate the cost in USD for token usage.

        Args:
            model: The model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        pricing = self._get_pricing(model)
        input_cost = (input_tokens * pricing["input"]) / 1_000_000
        output_cost = (output_tokens * pricing["output"]) / 1_000_000
        return input_cost + output_cost

    def record_usage(
        self,
        session_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> TokenUsage:
        """Record a token usage event.

        Args:
            session_id: The session identifier
            model: The model name used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            The created TokenUsage record
        """
        cost = self._calculate_cost(model, input_tokens, output_tokens)
        usage = TokenUsage(
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )
        self._usages = self._usages + [usage]
        self._save()
        logger.debug(
            f"Recorded usage: session={session_id}, model={model}, "
            f"tokens={input_tokens}/{output_tokens}, cost=${cost:.6f}"
        )
        return usage

    def get_costs_by_session(self, session_id: str) -> list[TokenUsage]:
        """Get all usage records for a session.

        Args:
            session_id: The session identifier

        Returns:
            List of TokenUsage records for the session
        """
        return [u for u in self._usages if u.session_id == session_id]

    def get_total_costs(
        self, since: Optional[datetime] = None
    ) -> dict:
        """Get total cost summary.

        Args:
            since: Optional datetime filter (only include records after this time)

        Returns:
            Dictionary with total costs and breakdowns
        """
        filtered = self._usages
        if since:
            filtered = [
                u
                for u in self._usages
                if datetime.fromisoformat(u.timestamp) >= since
            ]

        total_input = sum(u.input_tokens for u in filtered)
        total_output = sum(u.output_tokens for u in filtered)
        total_cost = sum(u.cost_usd for u in filtered)

        # Aggregate by model
        by_model: dict[str, dict] = {}
        for usage in filtered:
            if usage.model not in by_model:
                by_model[usage.model] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                    "call_count": 0,
                }
            by_model[usage.model]["input_tokens"] += usage.input_tokens
            by_model[usage.model]["output_tokens"] += usage.output_tokens
            by_model[usage.model]["cost_usd"] += usage.cost_usd
            by_model[usage.model]["call_count"] += 1

        return {
            "total_cost_usd": total_cost,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "call_count": len(filtered),
            "by_model": by_model,
        }

    def check_cost_limit(self, session_id: str, limit_usd: float) -> bool:
        """Check if a session has exceeded a cost limit.

        Args:
            session_id: The session identifier
            limit_usd: The cost limit in USD

        Returns:
            True if the limit is exceeded, False otherwise
        """
        session_usages = self.get_costs_by_session(session_id)
        total_cost = sum(u.cost_usd for u in session_usages)
        return total_cost > limit_usd

    def _load(self):
        """Load usage data from the persistence file."""
        try:
            if self._persist_path.exists():
                data = json.loads(self._persist_path.read_text(encoding="utf-8"))
                self._usages = [TokenUsage(**item) for item in data]
        except Exception as e:
            logger.warning(f"Failed to load token usage file: {e}")
            self._usages = []

    def _save(self):
        """Save usage data to the persistence file."""
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            data = [asdict(u) for u in self._usages]
            self._persist_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"Failed to save token usage file: {e}")
