"""Tests for CostService.

This module tests:
- Token usage recording
- Cost calculation by model
- Session-based cost aggregation
- Cost limit checking
"""

import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest

from app.services.cost_service import CostService, TokenUsage


class TestTokenUsage:
    """TokenUsage dataclass tests."""

    def test_token_usage_creation(self):
        """Test creating a TokenUsage instance."""
        usage = TokenUsage(
            timestamp="2024-01-01T00:00:00Z",
            session_id="test-session",
            model="gpt-4o-mini",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.000045,
        )
        assert usage.timestamp == "2024-01-01T00:00:00Z"
        assert usage.session_id == "test-session"
        assert usage.model == "gpt-4o-mini"
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.cost_usd == 0.000045


class TestCostService:
    """CostService class tests."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path, monkeypatch):
        """Set up test fixtures."""
        # Reset singleton before each test
        CostService._instance = None
        self.data_file = tmp_path / "token_usage.json"
        self.cost_service = CostService(persist_path=str(self.data_file))
        yield
        # Clean up after each test
        CostService._instance = None

    def test_singleton_pattern(self):
        """Test that CostService follows singleton pattern."""
        # Reset singleton for test
        CostService._instance = None
        service1 = CostService()
        service2 = CostService()
        assert service1 is service2
        # Clean up
        CostService._instance = None

    def test_record_usage_gpt4o_mini(self):
        """Test recording usage with GPT-4o-mini model."""
        usage = self.cost_service.record_usage(
            session_id="session-1",
            model="gpt-4o-mini",
            input_tokens=1000,
            output_tokens=500,
        )

        assert usage.session_id == "session-1"
        assert usage.model == "gpt-4o-mini"
        assert usage.input_tokens == 1000
        assert usage.output_tokens == 500
        # GPT-4o-mini: $0.15/1M input, $0.60/1M output
        # 1000 input * 0.15 / 1M = 0.00015
        # 500 output * 0.60 / 1M = 0.0003
        # Total: 0.00045
        assert abs(usage.cost_usd - 0.00045) < 0.0000001

    def test_record_usage_gpt4o(self):
        """Test recording usage with GPT-4o model."""
        usage = self.cost_service.record_usage(
            session_id="session-1",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
        )

        assert usage.model == "gpt-4o"
        # GPT-4o: $2.50/1M input, $10.00/1M output
        # 1000 input * 2.50 / 1M = 0.0025
        # 500 output * 10.00 / 1M = 0.005
        # Total: 0.0075
        assert abs(usage.cost_usd - 0.0075) < 0.0000001

    def test_record_usage_unknown_model(self):
        """Test recording usage with unknown model uses default rates."""
        usage = self.cost_service.record_usage(
            session_id="session-1",
            model="unknown-model",
            input_tokens=1000,
            output_tokens=500,
        )

        assert usage.model == "unknown-model"
        # Default rates (same as GPT-4o-mini)
        assert abs(usage.cost_usd - 0.00045) < 0.0000001

    def test_get_costs_by_session(self):
        """Test retrieving costs by session ID."""
        # Record multiple usages
        self.cost_service.record_usage("session-1", "gpt-4o-mini", 100, 50)
        self.cost_service.record_usage("session-1", "gpt-4o-mini", 200, 100)
        self.cost_service.record_usage("session-2", "gpt-4o", 150, 75)

        session_costs = self.cost_service.get_costs_by_session("session-1")

        assert len(session_costs) == 2
        assert all(c.session_id == "session-1" for c in session_costs)

    def test_get_costs_by_session_empty(self):
        """Test retrieving costs for non-existent session."""
        costs = self.cost_service.get_costs_by_session("non-existent")
        assert costs == []

    def test_get_total_costs(self):
        """Test getting total costs summary."""
        # Record multiple usages
        self.cost_service.record_usage("session-1", "gpt-4o-mini", 1000, 500)
        self.cost_service.record_usage("session-2", "gpt-4o", 500, 250)

        total = self.cost_service.get_total_costs()

        assert total["total_input_tokens"] == 1500
        assert total["total_output_tokens"] == 750
        # session-1: 0.00045, session-2: 0.00375 (500*2.5/1M + 250*10/1M)
        expected_cost = 0.00045 + 0.00375
        assert abs(total["total_cost_usd"] - expected_cost) < 0.0000001
        assert "by_model" in total
        assert "gpt-4o-mini" in total["by_model"]
        assert "gpt-4o" in total["by_model"]

    def test_get_total_costs_with_since_filter(self):
        """Test getting total costs with time filter."""
        now = datetime.now(timezone.utc)

        # Record usage
        self.cost_service.record_usage("session-1", "gpt-4o-mini", 100, 50)

        # Filter by future time - should return empty
        future = now + timedelta(hours=1)
        total = self.cost_service.get_total_costs(since=future)
        assert total["total_input_tokens"] == 0

    def test_check_cost_limit_under(self):
        """Test cost limit check when under limit."""
        self.cost_service.record_usage("session-1", "gpt-4o-mini", 1000, 500)
        # Cost is 0.00045

        is_over = self.cost_service.check_cost_limit("session-1", limit_usd=1.0)
        assert is_over is False

    def test_check_cost_limit_over(self):
        """Test cost limit check when over limit."""
        # Record usage that exceeds limit
        self.cost_service.record_usage("session-1", "gpt-4o", 1000000, 500000)
        # Cost: 2.5 + 5.0 = 7.5 USD

        is_over = self.cost_service.check_cost_limit("session-1", limit_usd=5.0)
        assert is_over is True

    def test_check_cost_limit_empty_session(self):
        """Test cost limit check for empty session."""
        is_over = self.cost_service.check_cost_limit("empty-session", limit_usd=1.0)
        assert is_over is False

    def test_persistence(self):
        """Test that data is persisted to file."""
        self.cost_service.record_usage("session-1", "gpt-4o-mini", 100, 50)

        # Check file exists
        assert self.data_file.exists()

        # Check content
        data = json.loads(self.data_file.read_text())
        assert len(data) == 1
        assert data[0]["session_id"] == "session-1"

    def test_load_existing_data(self):
        """Test loading existing data from file."""
        # Write initial data
        initial_data = [
            {
                "timestamp": "2024-01-01T00:00:00Z",
                "session_id": "existing-session",
                "model": "gpt-4o-mini",
                "input_tokens": 100,
                "output_tokens": 50,
                "cost_usd": 0.000045,
            }
        ]
        self.data_file.write_text(json.dumps(initial_data))

        # Create new instance - should load existing data
        CostService._instance = None
        new_service = CostService(persist_path=str(self.data_file))

        costs = new_service.get_costs_by_session("existing-session")
        assert len(costs) == 1
        assert costs[0].session_id == "existing-session"

        # Clean up
        CostService._instance = None

    def test_get_by_model_aggregation(self):
        """Test aggregation by model."""
        self.cost_service.record_usage("session-1", "gpt-4o-mini", 1000, 500)
        self.cost_service.record_usage("session-2", "gpt-4o-mini", 500, 250)
        self.cost_service.record_usage("session-3", "gpt-4o", 1000, 500)

        total = self.cost_service.get_total_costs()

        assert total["by_model"]["gpt-4o-mini"]["input_tokens"] == 1500
        assert total["by_model"]["gpt-4o-mini"]["output_tokens"] == 750
        assert total["by_model"]["gpt-4o"]["input_tokens"] == 1000
        assert total["by_model"]["gpt-4o"]["output_tokens"] == 500
