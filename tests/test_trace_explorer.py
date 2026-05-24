"""Tests for trace explorer API guard."""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.trace_explorer import (
    router, TraceFilter, TraceQueryRequest, TraceQueryService,
    MAX_FILTER_DEPTH, count_filter_depth
)


app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestTraceFilterValidation:
    """Tests for TraceFilter depth validation."""

    def test_valid_shallow_filter(self):
        filter_data = {"field": "status", "op": "eq", "value": "running"}
        f = TraceFilter(**filter_data)
        assert f.field == "status"

    def test_valid_nested_filter(self):
        filter_data = {
            "field": "status",
            "op": "eq",
            "value": "running",
            "nested": [
                {"field": "type", "op": "eq", "value": "worker"}
            ]
        }
        f = TraceFilter(**filter_data)
        assert len(f.nested) == 1

    def test_excessive_depth_rejected(self):
        # Create filter with depth > MAX_FILTER_DEPTH
        deep_filter = {"field": "l1", "op": "eq", "value": "v1"}
        for i in range(MAX_FILTER_DEPTH + 2):
            deep_filter = {
                "field": f"l{i}",
                "op": "eq",
                "value": f"v{i}",
                "nested": [deep_filter]
            }
        
        with pytest.raises(ValueError) as exc_info:
            TraceFilter(**deep_filter)
        
        assert "depth" in str(exc_info.value).lower()


class TestTraceQueryService:
    """Tests for TraceQueryService guard."""

    def test_validate_query_passes_valid_request(self):
        request = TraceQueryRequest(agent_id="agent1", limit=10)
        # Should not raise
        TraceQueryService.validate_query(request)

    def test_validate_query_rejects_deep_nesting(self):
        # Create nested filters at max depth
        nested = None
        for i in range(MAX_FILTER_DEPTH + 1):
            nested = [TraceFilter(field=f"f{i}", op="eq", value=f"v{i}", nested=nested)]
        
        request = TraceQueryRequest(filters=nested)
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            TraceQueryService.validate_query(request)
        
        assert exc_info.value.status_code == 400
        assert "depth" in str(exc_info.value.detail).lower()

    def test_execute_query_returns_results(self):
        request = TraceQueryRequest(agent_id="agent1", limit=10)
        result = TraceQueryService.execute_query(request)
        assert "traces" in result
        assert "total" in result


class TestTraceQueryEndpoint:
    """Tests for /traces/query endpoint."""

    def test_query_valid_request(self):
        response = client.post("/traces/query", json={
            "agent_id": "agent1",
            "limit": 10
        })
        assert response.status_code == 200
        assert "traces" in response.json()

    def test_query_with_shallow_filters(self):
        response = client.post("/traces/query", json={
            "agent_id": "agent1",
            "filters": [
                {"field": "status", "op": "eq", "value": "running"}
            ]
        })
        assert response.status_code == 200

    def test_query_rejects_deep_filters(self):
        # Create deeply nested filter
        filter_data = {"field": "l1", "op": "eq", "value": "v1"}
        for i in range(MAX_FILTER_DEPTH + 1):
            filter_data = {
                "field": f"l{i}",
                "op": "eq",
                "value": f"v{i}",
                "nested": [filter_data]
            }
        
        response = client.post("/traces/query", json={
            "agent_id": "agent1",
            "filters": [filter_data]
        })
        
        assert response.status_code == 400
        assert "depth" in response.json()["detail"].lower()

    def test_query_rejects_invalid_limit(self):
        response = client.post("/traces/query", json={
            "agent_id": "agent1",
            "limit": 0  # Below minimum
        })
        assert response.status_code == 422  # Validation error

    def test_query_rejects_excessive_limit(self):
        response = client.post("/traces/query", json={
            "agent_id": "agent1",
            "limit": 10000  # Above maximum
        })
        assert response.status_code == 422  # Validation error


class TestGetTraceEndpoint:
    """Tests for /traces/{trace_id} endpoint."""

    def test_get_trace(self):
        response = client.get("/traces/trace-123")
        assert response.status_code == 200
        assert response.json()["trace_id"] == "trace-123"


class TestCountFilterDepth:
    """Tests for count_filter_depth helper."""

    def test_empty_filters(self):
        assert count_filter_depth(None) == 0
        assert count_filter_depth([]) == 0

    def test_single_level(self):
        filters = [TraceFilter(field="f1", op="eq", value="v1")]
        assert count_filter_depth(filters) == 1

    def test_nested_levels(self):
        filters = [
            TraceFilter(
                field="f1",
                op="eq",
                value="v1",
                nested=[
                    TraceFilter(field="f2", op="eq", value="v2")
                ]
            )
        ]
        assert count_filter_depth(filters) == 2