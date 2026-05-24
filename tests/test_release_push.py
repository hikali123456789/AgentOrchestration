"""Tests for release push script."""

import pytest
from scripts.release_push import (
    ReleasePushValidator, RegistryTarget, PushValidationError
)


class TestRegistryTarget:
    """Tests for RegistryTarget dataclass."""

    def test_full_path(self):
        target = RegistryTarget(
            host="docker.io",
            namespace="agentorch",
            image="worker",
            tag="v1.0.0"
        )
        assert target.full_path == "docker.io/agentorch/worker:v1.0.0"


class TestParseTarget:
    """Tests for parse_target method."""

    def test_parse_full_reference(self):
        validator = ReleasePushValidator()
        target = validator.parse_target("docker.io/ns/img:tag")
        assert target.host == "docker.io"
        assert target.namespace == "ns"
        assert target.image == "img"
        assert target.tag == "tag"

    def test_parse_short_reference(self):
        validator = ReleasePushValidator()
        target = validator.parse_target("ns/img:tag")
        assert target.host == "docker.io"
        assert target.namespace == "ns"
        assert target.image == "img"

    def test_parse_no_tag(self):
        validator = ReleasePushValidator()
        target = validator.parse_target("docker.io/ns/img")
        assert target.tag == "latest"

    def test_parse_invalid_format(self):
        validator = ReleasePushValidator()
        with pytest.raises(PushValidationError):
            validator.parse_target("invalid")


class TestValidateTag:
    """Tests for tag validation."""

    def test_valid_semver(self):
        validator = ReleasePushValidator()
        assert validator.validate_tag("v1.0.0") is True
        assert validator.validate_tag("2.3.4") is True

    def test_valid_latest(self):
        validator = ReleasePushValidator()
        assert validator.validate_tag("latest") is True

    def test_valid_git_sha(self):
        validator = ReleasePushValidator()
        assert validator.validate_tag("abc1234") is True
        assert validator.validate_tag("abc1234567890123456789012345678901234567") is True

    def test_invalid_tag(self):
        validator = ReleasePushValidator()
        assert validator.validate_tag("invalid tag!") is False
        assert validator.validate_tag("") is False


class TestValidateRegistry:
    """Tests for registry allowlist validation."""

    def test_approved_registry(self):
        validator = ReleasePushValidator()
        target = RegistryTarget(
            host="docker.io",
            namespace="agentorch",
            image="worker",
            tag="v1.0.0"
        )
        assert validator.validate_registry(target) is True

    def test_unapproved_registry(self):
        validator = ReleasePushValidator()
        target = RegistryTarget(
            host="docker.io",
            namespace="unauthorized",
            image="worker",
            tag="v1.0.0"
        )
        assert validator.validate_registry(target) is False

    def test_custom_approved_registries(self):
        validator = ReleasePushValidator(approved_registries={("custom.io", "ns")})
        target = RegistryTarget(
            host="custom.io",
            namespace="ns",
            image="worker",
            tag="v1.0.0"
        )
        assert validator.validate_registry(target) is True


class TestValidate:
    """Tests for full validation."""

    def test_valid_image(self):
        validator = ReleasePushValidator()
        target = validator.validate("docker.io/agentorch/worker:v1.0.0")
        assert target.host == "docker.io"
        assert target.namespace == "agentorch"

    def test_invalid_tag_fails(self):
        validator = ReleasePushValidator()
        with pytest.raises(PushValidationError):
            validator.validate("docker.io/agentorch/worker:invalid!")

    def test_unapproved_registry_fails(self):
        validator = ReleasePushValidator()
        with pytest.raises(PushValidationError):
            validator.validate("docker.io/unauthorized/worker:v1.0.0")


class TestPush:
    """Tests for push method."""

    def test_push_valid(self):
        validator = ReleasePushValidator()
        assert validator.push("docker.io/agentorch/worker:v1.0.0", dry_run=True) is True

    def test_push_invalid_fails(self):
        validator = ReleasePushValidator()
        assert validator.push("docker.io/unauthorized/worker:v1.0.0", dry_run=True) is False

    def test_push_invalid_tag_fails(self):
        validator = ReleasePushValidator()
        assert validator.push("docker.io/agentorch/worker:bad tag!", dry_run=True) is False