"""Configuration management module."""

import os
import json
from typing import Any, Dict, Optional


class Config:
    def __init__(self, config_path: Optional[str] = None):
        self._data: Dict[str, Any] = {}
        if config_path:
            self.load(config_path)
        self._load_env_overrides()

    def load(self, path: str) -> None:
        with open(path) as f:
            self._data = json.load(f)

    def _load_env_overrides(self) -> None:
        prefix = "AO_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower().replace("_", ".")
                self._set_nested(config_key, value)

    def _set_nested(self, key: str, value: Any) -> None:
        parts = key.split(".")
        current = self._data
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def get(self, key: str, default: Any = None) -> Any:
        parts = key.split(".")
        current = self._data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return default
            else:
                return default
        return current

    def set(self, key: str, value: Any) -> None:
        self._set_nested(key, value)

    def to_dict(self) -> Dict:
        return self._data

    def to_redacted_dict(self, sensitive_keys=None) -> Dict:
        """Return a redacted config snapshot masking sensitive values."""
        import copy
        if sensitive_keys is None:
            sensitive_keys = {"password", "secret", "token", "key", "credential", "auth", "api_key", "private_key", "access_key"}
        result = copy.deepcopy(self._data)

        def _redact(obj, key_hint=""):
            lower_hint = key_hint.lower()
            # If parent's key is sensitive, all children are redacted
            force_redact = any(s in lower_hint for s in sensitive_keys)
            if isinstance(obj, dict):
                if force_redact:
                    # propagate the sensitive hint to all descendants
                    return {k: _redact(v, key_hint) for k, v in obj.items()}
                return {k: _redact(v, k) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_redact(v, key_hint) for v in obj]
            elif force_redact:
                return "***REDACTED***"
            else:
                for sensitive in sensitive_keys:
                    if sensitive in lower_hint:
                        return "***REDACTED***"
                return obj

        return _redact(result)

