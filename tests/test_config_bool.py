"""Tests for Config get_bool method."""

import pytest
from src.common.config import Config, ConfigError


class TestGetBool:
    def test_true_values(self):
        config = Config()
        config.set("flag", "true")
        assert config.get_bool("flag") is True

    def test_false_values(self):
        config = Config()
        config.set("flag", "false")
        assert config.get_bool("flag") is False

    def test_invalid_raises(self):
        config = Config()
        config.set("flag", "invalid")
        with pytest.raises(ConfigError):
            config.get_bool("flag")