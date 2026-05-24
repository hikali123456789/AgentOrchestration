"""Tests for worker protocol validator."""

import pytest
import time
from src.orchestrator.protocol import (
    WorkerProtocolValidator,
    WorkerProtocolSettings,
    ProtocolValidationError,
    create_validator_with_defaults
)


class TestWorkerProtocolSettings:
    """Tests for protocol settings."""

    def test_default_settings(self):
        settings = WorkerProtocolSettings()
        assert settings.ack_timeout == 30.0
        assert settings.visibility_timeout == 60.0

    def test_custom_settings(self):
        settings = WorkerProtocolSettings(ack_timeout=10.0, visibility_timeout=20.0)
        assert settings.ack_timeout == 10.0
        assert settings.visibility_timeout == 20.0


class TestWorkerProtocolValidator:
    """Tests for protocol validator."""

    def test_valid_settings_pass(self):
        settings = WorkerProtocolSettings(ack_timeout=10.0, visibility_timeout=30.0)
        validator = WorkerProtocolValidator(settings)
        assert validator.validate() is True

    def test_ack_timeout_equals_visibility_fails(self):
        settings = WorkerProtocolSettings(ack_timeout=30.0, visibility_timeout=30.0)
        validator = WorkerProtocolValidator(settings)
        with pytest.raises(ProtocolValidationError):
            validator.validate()

    def test_ack_timeout_exceeds_visibility_fails(self):
        settings = WorkerProtocolSettings(ack_timeout=60.0, visibility_timeout=30.0)
        validator = WorkerProtocolValidator(settings)
        with pytest.raises(ProtocolValidationError):
            validator.validate()

    def test_zero_ack_timeout_fails(self):
        settings = WorkerProtocolSettings(ack_timeout=0.0, visibility_timeout=30.0)
        validator = WorkerProtocolValidator(settings)
        with pytest.raises(ProtocolValidationError):
            validator.validate()

    def test_negative_ack_timeout_fails(self):
        settings = WorkerProtocolSettings(ack_timeout=-5.0, visibility_timeout=30.0)
        validator = WorkerProtocolValidator(settings)
        with pytest.raises(ProtocolValidationError):
            validator.validate()

    def test_zero_visibility_timeout_fails(self):
        settings = WorkerProtocolSettings(ack_timeout=10.0, visibility_timeout=0.0)
        validator = WorkerProtocolValidator(settings)
        with pytest.raises(ProtocolValidationError):
            validator.validate()


class TestTaskClaimValidation:
    """Tests for task claim validation."""

    def test_valid_claim(self):
        settings = WorkerProtocolSettings(ack_timeout=10.0, visibility_timeout=30.0)
        validator = WorkerProtocolValidator(settings)
        task = {"id": "task1", "claimed_at": time.time()}
        assert validator.validate_task_claim(task) is True

    def test_expired_claim(self):
        settings = WorkerProtocolSettings(ack_timeout=1.0, visibility_timeout=10.0)
        validator = WorkerProtocolValidator(settings)
        task = {"id": "task1", "claimed_at": time.time() - 5.0}  # 5s ago
        assert validator.validate_task_claim(task) is False

    def test_missing_claim_timestamp(self):
        settings = WorkerProtocolSettings(ack_timeout=10.0, visibility_timeout=30.0)
        validator = WorkerProtocolValidator(settings)
        task = {"id": "task1"}
        assert validator.validate_task_claim(task) is False


class TestFactoryFunction:
    """Tests for create_validator_with_defaults."""

    def test_safe_defaults(self):
        validator = create_validator_with_defaults()
        assert validator.settings.ack_timeout == 10.0
        assert validator.settings.visibility_timeout == 30.0
        # Should pass validation
        assert validator.validate() is True

    def test_ack_less_than_visibility(self):
        validator = create_validator_with_defaults()
        assert validator.settings.ack_timeout < validator.settings.visibility_timeout


class TestErrorMessages:
    """Tests for error reporting."""

    def test_error_includes_timeout_values(self):
        settings = WorkerProtocolSettings(ack_timeout=60.0, visibility_timeout=30.0)
        validator = WorkerProtocolValidator(settings)
        try:
            validator.validate()
        except ProtocolValidationError as e:
            assert "60.0" in str(e)
            assert "30.0" in str(e)

    def test_get_errors_after_validation(self):
        settings = WorkerProtocolSettings(ack_timeout=60.0, visibility_timeout=30.0)
        validator = WorkerProtocolValidator(settings)
        try:
            validator.validate()
        except ProtocolValidationError:
            pass
        errors = validator.get_errors()
        assert len(errors) > 0