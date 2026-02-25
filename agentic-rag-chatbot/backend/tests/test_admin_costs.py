"""Tests for Admin Costs API endpoints.

This module tests:
- GET /api/admin/costs endpoint
- GET /api/admin/costs/check-limit endpoint
- Authentication requirements
"""

import pytest


@pytest.fixture(autouse=True)
def setup():
    """Set up test fixtures."""
    # Reset singleton before each test
    from app.services.cost_service import CostService
    CostService._instance = None
    yield
    CostService._instance = None


class TestCostServiceIntegration:
    """Tests for CostService integration with API."""

    def test_record_and_retrieve_costs(self):
        """Test recording and retrieving costs."""
        from app.services.cost_service import CostService

        service = CostService.get_instance()

        # Record usage
        usage = service.record_usage("session-1", "gpt-4o-mini", 100, 50)

        assert usage.session_id == "session-1"
        assert usage.model == "gpt-4o-mini"
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50

        # Get costs by session
        session_costs = service.get_costs_by_session("session-1")
        assert len(session_costs) == 1
        assert session_costs[0].session_id == "session-1"

    def test_cost_limit_check(self):
        """Test cost limit checking."""
        from app.services.cost_service import CostService

        service = CostService.get_instance()

        # Record low usage
        service.record_usage("session-1", "gpt-4o-mini", 100, 50)

        # Check limit - should be under
        is_over = service.check_cost_limit("session-1", limit_usd=1.0)
        assert is_over is False

    def test_cost_limit_exceeded(self):
        """Test cost limit exceeded."""
        from app.services.cost_service import CostService

        service = CostService.get_instance()

        # Record high usage
        service.record_usage("session-2", "gpt-4o", 1000000, 500000)
        # Cost: 2.5 + 5.0 = 7.5 USD

        # Check limit - should be over
        is_over = service.check_cost_limit("session-2", limit_usd=5.0)
        assert is_over is True

    def test_total_costs_aggregation(self):
        """Test total costs aggregation."""
        from app.services.cost_service import CostService

        service = CostService.get_instance()

        # Record multiple usages
        service.record_usage("session-1", "gpt-4o-mini", 1000, 500)
        service.record_usage("session-2", "gpt-4o", 500, 250)

        total = service.get_total_costs()

        assert total["total_input_tokens"] == 1500
        assert total["total_output_tokens"] == 750
        assert "by_model" in total
        assert "gpt-4o-mini" in total["by_model"]
        assert "gpt-4o" in total["by_model"]

    def test_authentication_token_creation(self):
        """Test JWT token creation for authentication."""
        from app.auth.jwt_handler import create_access_token

        token = create_access_token({"sub": "test-user", "role": "admin"})
        assert token is not None
        assert isinstance(token, str)


class TestAdminCostsAPIEndpoints:
    """Tests for Admin API endpoint definitions."""

    def test_costs_endpoint_exists(self):
        """Test that costs endpoint is defined in admin router."""
        from app.api.admin import router

        # Get all routes
        routes = [route.path for route in router.routes]

        assert "/costs" in routes
        assert "/costs/check-limit" in routes

    def test_costs_endpoint_methods(self):
        """Test that costs endpoint uses GET method."""
        from app.api.admin import router

        costs_route = None
        for route in router.routes:
            if route.path == "/costs":
                costs_route = route
                break

        assert costs_route is not None
        assert "GET" in costs_route.methods
