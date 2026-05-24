"""Tests for malformed payload handling."""

import pytest
from src.orchestrator.scheduler import (
    TaskScheduler, validate_task_payload, MalformedPayloadError
)


class TestValidateTaskPayload:
    """Tests for payload validation."""

    def test_valid_payload(self):
        errors = validate_task_payload({"type": "test"})
        assert errors == []

    def test_missing_type(self):
        errors = validate_task_payload({"payload": {}})
        assert "type" in errors[0].lower()

    def test_invalid_type_field(self):
        errors = validate_task_payload({"type": 123})
        assert len(errors) > 0

    def test_not_dict(self):
        errors = validate_task_payload("not a dict")
        assert "dictionary" in errors[0].lower()

    def test_invalid_priority(self):
        errors = validate_task_payload({"type": "test", "priority": "high"})
        assert len(errors) > 0


class TestTaskSchedulerValidation:
    """Tests for TaskScheduler with validation."""

    def test_enqueue_valid_payload(self):
        scheduler = TaskScheduler()
        task_id = scheduler.enqueue({"type": "test"})
        assert task_id is not None

    def test_enqueue_missing_type_strict_mode(self):
        scheduler = TaskScheduler(strict_validation=True)
        with pytest.raises(MalformedPayloadError):
            scheduler.enqueue({"payload": {}})

    def test_enqueue_missing_type_non_strict(self):
        scheduler = TaskScheduler(strict_validation=False)
        task_id = scheduler.enqueue({"payload": {}})
        assert task_id is not None

    def test_reject_task(self):
        scheduler = TaskScheduler()
        task_id = scheduler.enqueue({"type": "test"})
        import asyncio
        task = asyncio.run(scheduler.dequeue())
        assert scheduler.reject(task["id"], "malformed") is True

    def test_reject_nonexistent_task(self):
        scheduler = TaskScheduler()
        assert scheduler.reject("nonexistent", "reason") is False


class TestMalformedPayloadError:
    """Tests for MalformedPayloadError."""

    def test_error_message(self):
        error = MalformedPayloadError("test error")
        assert str(error) == "test error"