"""Tests for queue capacity limiter."""

import pytest
import threading
import time
from src.orchestrator.capacity import (
    QueueCapacityLimiter, CapacityExceededError,
    create_capacity_limiter
)


class TestQueueCapacityLimiter:
    """Tests for capacity limiter."""

    def test_set_and_get_capacity(self):
        limiter = QueueCapacityLimiter()
        limiter.set_capacity("test_queue", 10)
        assert limiter.get_capacity("test_queue") == 10

    def test_default_capacity(self):
        limiter = QueueCapacityLimiter(default_capacity=50)
        assert limiter.get_capacity("unknown_queue") == 50

    def test_reserve_and_release(self):
        limiter = QueueCapacityLimiter()
        limiter.set_capacity("test", 2)
        
        # Reserve capacity
        assert limiter._reserve("test", "res1") is True
        assert limiter._reserve("test", "res2") is True
        assert limiter.get_available("test") == 0
        
        # Third reserve should fail
        assert limiter._reserve("test", "res3") is False
        
        # Release and reserve again
        assert limiter._release("res1") is True
        assert limiter._reserve("test", "res3") is True

    def test_release_nonexistent(self):
        limiter = QueueCapacityLimiter()
        assert limiter._release("nonexistent") is False

    def test_double_release(self):
        limiter = QueueCapacityLimiter()
        limiter.set_capacity("test", 2)
        limiter._reserve("test", "res1")
        assert limiter._release("res1") is True
        assert limiter._release("res1") is False  # Already released


class TestAcquireContextManager:
    """Tests for acquire context manager."""

    def test_acquire_success(self):
        limiter = QueueCapacityLimiter()
        limiter.set_capacity("test", 1)
        
        with limiter.acquire("test") as reserved:
            assert reserved is True

    def test_acquire_auto_release(self):
        limiter = QueueCapacityLimiter()
        limiter.set_capacity("test", 1)
        
        with limiter.acquire("test") as reserved:
            pass
        
        # Capacity should be released
        assert limiter.get_available("test") == 1

    def test_acquire_capacity_exceeded(self):
        limiter = QueueCapacityLimiter()
        limiter.set_capacity("test", 1)
        
        with limiter.acquire("test"):
            with pytest.raises(CapacityExceededError):
                with limiter.acquire("test"):
                    pass


class TestExecuteWithCapacity:
    """Tests for execute_with_capacity."""

    def test_execute_success(self):
        limiter = QueueCapacityLimiter()
        limiter.set_capacity("test", 1)
        
        def operation():
            return "success"
        
        result = limiter.execute_with_capacity("test", operation)
        assert result == "success"
        # Capacity released
        assert limiter.get_available("test") == 1

    def test_execute_failure_releases_capacity(self):
        limiter = QueueCapacityLimiter()
        limiter.set_capacity("test", 1)
        
        def failing_operation():
            raise ValueError("test error")
        
        with pytest.raises(ValueError):
            limiter.execute_with_capacity("test", failing_operation)
        
        # Capacity should be released even on failure
        assert limiter.get_available("test") == 1

    def test_execute_no_capacity(self):
        limiter = QueueCapacityLimiter()
        limiter.set_capacity("test", 1)
        
        # Reserve all capacity
        limiter._reserve("test", "existing")
        
        def operation():
            return "success"
        
        with pytest.raises(CapacityExceededError):
            limiter.execute_with_capacity("test", operation)


class TestMetrics:
    """Tests for capacity metrics."""

    def test_get_metrics(self):
        limiter = QueueCapacityLimiter()
        limiter.set_capacity("queue1", 10)
        limiter.set_capacity("queue2", 20)
        limiter._reserve("queue1", "res1")
        
        metrics = limiter.get_metrics()
        assert "queue1" in metrics
        assert metrics["queue1"]["capacity"] == 10
        assert metrics["queue1"]["reserved"] == 1
        assert metrics["queue1"]["available"] == 9
        assert 0 < metrics["queue1"]["utilization"] < 1


class TestFactory:
    """Tests for factory function."""

    def test_create_capacity_limiter(self):
        limiter = create_capacity_limiter(capacity=100)
        assert limiter.get_capacity("any") == 100


class TestThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_reserves(self):
        limiter = QueueCapacityLimiter()
        limiter.set_capacity("test", 100)
        
        results = []
        def reserve_many():
            for i in range(10):
                success = limiter._reserve("test", f"thread-{threading.current_thread().ident}-{i}")
                results.append(success)
        
        threads = [threading.Thread(target=reserve_many) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have exactly 100 successful reserves
        assert sum(results) == 100