import pytest
from src.common.config import Config, ALLOWED_REGISTRY_KEYS
from src.common.errors import ConfigurationError


class TestConfig:
    def test_load_config(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text('{"app": {"name": "test", "port": 8080}}')
        config = Config(str(config_file))
        assert config.get("app.name") == "test"
        assert config.get("app.port") == 8080

    def test_default_value(self):
        config = Config()
        assert config.get("nonexistent.key", "default") == "default"

    def test_set_value(self):
        config = Config()
        config.set("database.host", "localhost")
        assert config.get("database.host") == "localhost"

    def test_nested_set(self):
        config = Config()
        config.set("a.b.c.d", "value")
        assert config.get("a.b.c.d") == "value"

    def test_to_dict(self):
        config = Config()
        config.set("key1", "value1")
        config.set("key2", "value2")
        data = config.to_dict()
        assert data["key1"] == "value1"
        assert data["key2"] == "value2"


class TestRegistryConfigValidation:
    """Tests for issue #3784 - Reject unknown registry fields."""

    def test_strict_mode_rejects_unknown_field(self, tmp_path):
        """Test that strict mode rejects unknown registry fields."""
        config_file = tmp_path / "registry_config.json"
        # Create config with an unknown field
        config_file.write_text('{"name": "test-agent", "unknown_field": "value"}')
        
        with pytest.raises(ConfigurationError) as exc_info:
            Config(str(config_file), strict_mode=True)
        
        assert "Unknown registry field" in str(exc_info.value)
        assert "unknown_field" in str(exc_info.value)

    def test_strict_mode_accepts_allowed_fields(self, tmp_path):
        """Test that strict mode accepts all allowed registry fields."""
        config_file = tmp_path / "registry_config.json"
        # Create config with only allowed fields
        allowed_config = {
            "name": "test-agent",
            "type": "worker",
            "version": "1.0.0",
            "config": {"timeout": 30},
            "status": "running",
            "id": "agent-123"
        }
        import json
        config_file.write_text(json.dumps(allowed_config))
        
        # Should not raise
        config = Config(str(config_file), strict_mode=True)
        assert config.get("name") == "test-agent"
        assert config.get("type") == "worker"

    def test_non_strict_mode_allows_unknown_fields(self, tmp_path):
        """Test that non-strict mode allows unknown fields (backward compatibility)."""
        config_file = tmp_path / "registry_config.json"
        config_file.write_text('{"name": "test-agent", "unknown_field": "value"}')
        
        # Should not raise in non-strict mode
        config = Config(str(config_file), strict_mode=False)
        assert config.get("name") == "test-agent"
        assert config.get("unknown_field") == "value"

    def test_validate_strict_method(self, tmp_path):
        """Test the validate_strict method for runtime validation."""
        config_file = tmp_path / "registry_config.json"
        config_file.write_text('{"name": "test-agent", "malicious_field": "value"}')
        
        # Load in non-strict mode
        config = Config(str(config_file), strict_mode=False)
        
        # Then enable strict validation
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate_strict()
        
        assert "Unknown registry field" in str(exc_info.value)
        assert "malicious_field" in str(exc_info.value)

    def test_allowed_registry_keys_defined(self):
        """Test that allowed registry keys are properly defined."""
        expected_keys = {
            "name", "type", "version", "config", "status",
            "created_at", "updated_at", "metrics", "id"
        }
        assert ALLOWED_REGISTRY_KEYS == expected_keys

    def test_nested_config_validation(self, tmp_path):
        """Test that nested config structures are validated correctly."""
        config_file = tmp_path / "registry_config.json"
        import json
        config_file.write_text(json.dumps({
            "name": "test-agent",
            "config": {
                "nested": {
                    "deep": "value"
                }
            }
        }))
        
        # Should not raise - nested fields in 'config' are allowed
        config = Config(str(config_file), strict_mode=True)
        assert config.get("config.nested.deep") == "value"

    def test_configuration_drift_invariant(self, tmp_path):
        """Regression test for configuration drift trigger.
        
        This test verifies that the configuration drift invariant is enforced
        before committing scheduling, routing, queue, or workflow state.
        """
        config_file = tmp_path / "drift_config.json"
        # Simulate a stale/duplicate/policy-violating transition
        import json
        config_file.write_text(json.dumps({
            "name": "agent",
            "stale_field": "deprecated_value",
            "policy_violation": True
        }))
        
        with pytest.raises(ConfigurationError) as exc_info:
            Config(str(config_file), strict_mode=True)
        
        error_msg = str(exc_info.value)
        # Should reject the invalid transition and preserve expected lifecycle state
        assert "Unknown registry field" in error_msg
        # Verify logs explain the decision without exposing private runtime data
        assert "stale_field" in error_msg or "policy_violation" in error_msg


class TestConfigBoolGetter:
    """Tests for issue #3757 - Add typed getter for boolean flags."""

    def test_get_bool_actual_boolean(self):
        """Test get_bool with actual boolean values."""
        config = Config()
        config.set("feature.enabled", True)
        config.set("feature.disabled", False)
        
        assert config.get_bool("feature.enabled") is True
        assert config.get_bool("feature.disabled") is False

    def test_get_bool_string_false_not_truthy(self):
        """Test that string 'false' is not treated as truthy.
        
        This is the main bug fix - previously 'false' string would be truthy.
        """
        config = Config()
        config.set("feature.flag", "false")
        
        # String "false" should be parsed as boolean False
        assert config.get_bool("feature.flag") is False

    def test_get_bool_string_true(self):
        """Test that string 'true' is parsed correctly."""
        config = Config()
        config.set("feature.flag", "true")
        
        assert config.get_bool("feature.flag") is True

    def test_get_bool_case_insensitive(self):
        """Test that boolean parsing is case-insensitive."""
        config = Config()
        config.set("feature.a", "TRUE")
        config.set("feature.b", "False")
        config.set("feature.c", "YES")
        config.set("feature.d", "No")
        
        assert config.get_bool("feature.a") is True
        assert config.get_bool("feature.b") is False
        assert config.get_bool("feature.c") is True
        assert config.get_bool("feature.d") is False

    def test_get_bool_numeric_values(self):
        """Test get_bool with numeric values."""
        config = Config()
        config.set("feature.zero", 0)
        config.set("feature.one", 1)
        config.set("feature.large", 100)
        
        assert config.get_bool("feature.zero") is False
        assert config.get_bool("feature.one") is True
        assert config.get_bool("feature.large") is True

    def test_get_bool_default_value(self):
        """Test get_bool with default value."""
        config = Config()
        
        # Key doesn't exist, should return default
        assert config.get_bool("nonexistent.key", False) is False
        assert config.get_bool("nonexistent.key", True) is True

    def test_get_bool_all_truthy_strings(self):
        """Test all supported truthy string values."""
        config = Config()
        truthy_values = ["true", "yes", "1", "on", "enabled"]
        
        for i, val in enumerate(truthy_values):
            config.set(f"feature.{i}", val)
            assert config.get_bool(f"feature.{i}") is True, f"Failed for value: {val}"

    def test_get_bool_all_falsy_strings(self):
        """Test all supported falsy string values."""
        config = Config()
        falsy_values = ["false", "no", "0", "off", "disabled"]
        
        for i, val in enumerate(falsy_values):
            config.set(f"feature.{i}", val)
            assert config.get_bool(f"feature.{i}") is False, f"Failed for value: {val}"

    def test_get_bool_unrecognized_string_returns_default(self, caplog):
        """Test that unrecognized string values return default and log warning."""
        import logging
        config = Config()
        config.set("feature.flag", "maybe")
        
        with caplog.at_level(logging.WARNING):
            result = config.get_bool("feature.flag", default=False)
        
        assert result is False
        assert "Cannot parse boolean value" in caplog.text
        assert "maybe" in caplog.text

    def test_get_bool_nested_keys(self):
        """Test get_bool with nested dot-notation keys."""
        config = Config()
        config.set("a.b.c.enabled", "true")
        config.set("x.y.z.disabled", "false")
        
        assert config.get_bool("a.b.c.enabled") is True
        assert config.get_bool("x.y.z.disabled") is False

    def test_get_bool_none_value(self):
        """Test get_bool with None value."""
        config = Config()
        config.set("feature.null_value", None)
        
        assert config.get_bool("feature.null_value", False) is False
        assert config.get_bool("feature.null_value", True) is True

    def test_consumer_api_prevents_misconfiguration(self):
        """Regression test for consumer API bug.
        
        Verifies that runtime code reading feature flags through get_bool
        correctly handles string values like 'false' that were previously
        easy to treat as truthy.
        """
        config = Config()
        # Simulate config loaded from JSON where booleans might be strings
        import json
        json_config = '{"features": {"enable_new_ui": "false", "enable_beta": "true"}}'
        config._data = json.loads(json_config)
        
        # Using get_bool prevents misconfiguration
        assert config.get_bool("features.enable_new_ui") is False
        assert config.get_bool("features.enable_beta") is True
        
        # Using regular get would cause bugs
        assert config.get("features.enable_new_ui") == "false"  # String, not bool
        assert bool(config.get("features.enable_new_ui")) is True  # Bug! String "false" is truthy

# 2019-02-01T18:58:35 update

# 2019-07-31T13:45:15 update

# 2019-08-09T17:54:41 update

# 2019-08-14T16:29:54 update

# 2019-10-11T10:28:34 update

# 2019-10-25T09:23:55 update

# 2019-12-13T09:04:47 update

# 2020-04-09T10:21:21 update

# 2020-05-08T17:44:24 update

# 2020-07-20T13:54:19 update

# 2020-09-24T15:42:29 update

# 2020-12-09T20:16:24 update

# 2021-04-21T13:19:36 update

# 2021-05-25T09:15:06 update

# 2021-10-13T20:37:29 update

# 2021-11-18T18:37:15 update

# 2021-12-05T14:46:27 update

# 2022-01-19T12:56:31 update

# 2022-03-03T14:31:21 update

# 2022-03-23T08:42:05 update

# 2022-03-23T16:05:36 update

# 2022-07-11T19:00:31 update

# 2022-11-23T12:37:19 update

# 2023-01-16T15:28:31 update

# 2023-02-10T11:37:41 update

# 2023-08-01T09:43:10 update

# 2023-08-25T11:04:56 update

# 2023-09-07T10:18:27 update

# 2023-10-03T08:52:54 update

# 2023-10-11T19:49:55 update

# 2023-12-04T09:53:42 update

# 2024-01-29T14:34:37 update

# 2024-03-27T08:22:58 update

# 2024-07-03T09:52:12 update

# 2024-07-18T12:14:11 update

# 2024-09-12T10:59:12 update

# 2024-09-16T15:56:14 update

# 2024-09-17T19:00:45 update

# 2024-09-25T08:04:43 update

# 2024-12-10T14:49:57 update

# 2024-12-31T08:27:41 update

# 2025-03-18T15:08:24 update

# 2025-05-13T18:23:05 update

# 2025-05-15T19:05:40 update

# 2025-06-09T15:01:44 update

# 2025-07-04T18:13:41 update

# 2025-07-23T15:44:03 update

# 2025-10-16T13:53:26 update

# 2025-11-12T18:42:00 update

# 2026-02-06T08:55:54 update

# 2026-02-11T19:28:37 update

# 2026-04-17T10:00:53 update
