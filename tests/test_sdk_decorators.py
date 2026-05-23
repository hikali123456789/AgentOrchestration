"""Tests for SDK decorators — task metadata introspection."""

import asyncio
import pytest
from src.sdk.decorators import task, on_event


class TestTaskDecoratorMetadata:
    """Verify __task_config__ is accessible on the returned wrapper."""

    def test_task_config_on_wrapper(self):
        """The task decorator must attach __task_config__ to the wrapper, not just the original."""

        @task(name="process_order", retries=3, timeout=60)
        async def handler(order_id: str) -> str:
            return f"processed {order_id}"

        # The returned value is the wrapper; it should carry task metadata
        assert hasattr(handler, "__task_config__"), (
            "wrapper must expose __task_config__ for task discovery"
        )
        cfg = handler.__task_config__
        assert cfg["name"] == "process_order"
        assert cfg["retries"] == 3
        assert cfg["timeout"] == 60

    def test_default_name_is_func_name(self):
        """When no name is given, __task_config__.name falls back to __name__."""

        @task(retries=1, timeout=120)
        async def backup() -> str:
            return "done"

        assert backup.__task_config__["name"] == "backup"

    @pytest.mark.asyncio
    async def test_wrapper_still_invokes_func(self):
        """The wrapper must still call the original function correctly."""

        @task(name="noop")
        async def identity(x: int) -> int:
            return x * 2

        result = await identity(21)
        assert result == 42


class TestOnEventDecoratorMetadata:
    """Verify __event_handler__ is accessible on the returned wrapper."""

    def test_event_handler_on_wrapper(self):
        """on_event must attach __event_handler__ to the wrapper."""

        @on_event("pipeline.start")
        async def on_pipeline_start(payload: dict) -> None:
            pass

        assert hasattr(on_pipeline_start, "__event_handler__"), (
            "wrapper must expose __event_handler__ for event routing"
        )
        assert on_pipeline_start.__event_handler__ == "pipeline.start"

    @pytest.mark.asyncio
    async def test_event_wrapper_still_invokes_func(self):
        """The event wrapper must still call the original function."""

        calls = []

        @on_event("agent.ready")
        async def on_ready(payload: dict) -> None:
            calls.append(payload)

        await on_ready({"id": 1})
        assert len(calls) == 1
        assert calls[0] == {"id": 1}
