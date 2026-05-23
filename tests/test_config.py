import pytest
from src.common.config import Config


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

    def test_to_redacted_dict(self):
        config = Config()
        config.set("app.name", "myapp")
        config.set("db.password", "s3cret!")
        config.set("api.token", "tok123")
        config.set("api.key", "key456")
        config.set("nested.secret.value", "hidden")
        config.set("public.url", "http://example.com")
        data = config.to_redacted_dict()
        # sensitive values should be redacted
        assert data["db"]["password"] == "***REDACTED***"
        assert data["api"]["token"] == "***REDACTED***"
        assert data["api"]["key"] == "***REDACTED***"
        assert data["nested"]["secret"]["value"] == "***REDACTED***"
        # non-sensitive should remain
        assert data["app"]["name"] == "myapp"
        assert data["public"]["url"] == "http://example.com"
        # original to_dict should be unaffected
        original = config.to_dict()
        assert original["db"]["password"] == "s3cret!"
        assert "***REDACTED***" not in str(original)

    def test_to_redacted_dict_custom_keys(self):
        config = Config()
        config.set("db.host", "localhost")
        config.set("db.name", "mydb")
        data = config.to_redacted_dict(sensitive_keys={"host", "name"})
        assert data["db"]["host"] == "***REDACTED***"
        assert data["db"]["name"] == "***REDACTED***"

    def test_to_redacted_dict_lists(self):
        config = Config()
        config.set("servers", [{"host":"s1", "password":"p1"}, {"host":"s2", "password":"p2"}])
        data = config.to_redacted_dict()
        assert data["servers"][0]["host"] == "s1"
        assert data["servers"][0]["password"] == "***REDACTED***"
        assert data["servers"][1]["password"] == "***REDACTED***"
