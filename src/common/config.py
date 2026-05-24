"""Configuration management module."""
import os
import json
from typing import Any, Dict, Optional


class ConfigError(Exception):
    """Raised when configuration operation fails."""
    pass


class Config:
    # Accepted boolean true values (case-insensitive)
    TRUE_VALUES = {"true", "yes", "1", "on", "enabled"}
    # Accepted boolean false values (case-insensitive)
    FALSE_VALUES = {"false", "no", "0", "off", "disabled"}
    
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
    
    def get_bool(self, key: str, default: Optional[bool] = None) -> bool:
        """
        Get a boolean configuration value.
        
        Accepted true values (case-insensitive): true, yes, 1, on, enabled
        Accepted false values (case-insensitive): false, no, 0, off, disabled
        
        Args:
            key: Configuration key (dot notation)
            default: Default value if key not found
            
        Returns:
            Boolean value
            
        Raises:
            ConfigError: If value is not a valid boolean string
        """
        value = self.get(key)
        
        if value is None:
            if default is not None:
                return default
            raise ConfigError(f"Configuration key '{key}' not found and no default provided")
        
        # Handle actual booleans
        if isinstance(value, bool):
            return value
        
        # Handle strings
        if isinstance(value, str):
            lower_value = value.lower().strip()
            if lower_value in self.TRUE_VALUES:
                return True
            if lower_value in self.FALSE_VALUES:
                return False
            raise ConfigError(
                f"Invalid boolean value for '{key}': '{value}'. "
                f"Accepted true: {self.TRUE_VALUES}, "
                f"Accepted false: {self.FALSE_VALUES}"
            )
        
        # Handle integers
        if isinstance(value, int):
            return bool(value)
        
        raise ConfigError(
            f"Cannot convert value for '{key}' to boolean: {type(value).__name__}"
        )
    
    def set(self, key: str, value: Any) -> None:
        self._set_nested(key, value)
    
    def to_dict(self) -> Dict:
        return self._data