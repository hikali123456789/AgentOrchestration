"""Worker protocol validator with ack timeout and visibility checks."""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WorkerProtocolSettings:
    """Worker protocol configuration settings."""
    ack_timeout: float = 30.0  # Time to acknowledge task
    visibility_timeout: float = 60.0  # Time before task becomes visible again
    max_retries: int = 3


class ProtocolValidationError(Exception):
    """Raised when protocol settings are invalid."""
    pass


class WorkerProtocolValidator:
    """
    Validates worker protocol settings to ensure ack timeout exceeds visibility.
    
    Prevents jobs from being duplicated, starved, or lost due to
    misconfigured timeout settings.
    """
    
    def __init__(self, settings: Optional[WorkerProtocolSettings] = None):
        self.settings = settings or WorkerProtocolSettings()
        self._validation_errors: list = []
    
    def validate(self) -> bool:
        """
        Validate protocol settings.
        
        Returns:
            True if valid, False otherwise
            
        Raises:
            ProtocolValidationError: In strict mode with invalid settings
        """
        self._validation_errors = []
        
        # Core invariant: ack timeout must be less than visibility timeout
        if self.settings.ack_timeout >= self.settings.visibility_timeout:
            error = (
                f"ack_timeout ({self.settings.ack_timeout}s) must be less than "
                f"visibility_timeout ({self.settings.visibility_timeout}s)"
            )
            self._validation_errors.append(error)
            logger.error(f"Protocol validation failed: {error}")
            raise ProtocolValidationError(error)
        
        # Ack timeout must be positive
        if self.settings.ack_timeout <= 0:
            error = f"ack_timeout must be positive, got {self.settings.ack_timeout}"
            self._validation_errors.append(error)
            logger.error(f"Protocol validation failed: {error}")
            raise ProtocolValidationError(error)
        
        # Visibility timeout must be positive
        if self.settings.visibility_timeout <= 0:
            error = f"visibility_timeout must be positive, got {self.settings.visibility_timeout}"
            self._validation_errors.append(error)
            logger.error(f"Protocol validation failed: {error}")
            raise ProtocolValidationError(error)
        
        logger.info(
            f"Protocol settings validated: ack={self.settings.ack_timeout}s, "
            f"visibility={self.settings.visibility_timeout}s"
        )
        return True
    
    def validate_task_claim(self, task: Dict[str, Any]) -> bool:
        """
        Validate a task claim against protocol settings.
        
        Args:
            task: Task dictionary with claim metadata
            
        Returns:
            True if claim is valid
        """
        claimed_at = task.get("claimed_at")
        if not claimed_at:
            logger.warning(f"Task {task.get('id')} has no claim timestamp")
            return False
        
        # Check if claim is still within ack timeout
        import time
        elapsed = time.time() - claimed_at
        
        if elapsed > self.settings.ack_timeout:
            logger.warning(
                f"Task {task.get('id')} claim expired: "
                f"elapsed={elapsed:.1f}s > ack_timeout={self.settings.ack_timeout}s"
            )
            return False
        
        return True
    
    def get_errors(self) -> list:
        """Return list of validation errors."""
        return self._validation_errors.copy()


def create_validator_with_defaults() -> WorkerProtocolValidator:
    """Factory function to create validator with safe defaults."""
    # Safe defaults: ack_timeout (10s) < visibility_timeout (30s)
    settings = WorkerProtocolSettings(
        ack_timeout=10.0,
        visibility_timeout=30.0,
        max_retries=3
    )
    return WorkerProtocolValidator(settings)