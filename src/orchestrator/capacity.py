"""Queue capacity limiter with transaction rollback support."""

import logging
import threading
from typing import Dict, Optional, Callable
from contextlib import contextmanager
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CapacityReservation:
    """Represents a reserved capacity slot."""
    queue_name: str
    reserved_at: float
    released: bool = False


class CapacityExceededError(Exception):
    """Raised when queue capacity is exceeded."""
    pass


class QueueCapacityLimiter:
    """
    Queue capacity limiter with atomic reserve/release and rollback support.
    
    Ensures capacity is released when enqueue rolls back, preventing
    capacity leaks and stale transitions.
    """
    
    def __init__(self, default_capacity: int = 100):
        self._capacities: Dict[str, int] = {}
        self._reserved: Dict[str, int] = {}
        self._default_capacity = default_capacity
        self._lock = threading.RLock()
        self._reservations: Dict[str, CapacityReservation] = {}
    
    def set_capacity(self, queue_name: str, capacity: int) -> None:
        """Set capacity limit for a queue."""
        with self._lock:
            self._capacities[queue_name] = capacity
            self._reserved.setdefault(queue_name, 0)
    
    def get_capacity(self, queue_name: str) -> int:
        """Get capacity limit for a queue."""
        with self._lock:
            return self._capacities.get(queue_name, self._default_capacity)
    
    def get_available(self, queue_name: str) -> int:
        """Get available capacity for a queue."""
        with self._lock:
            capacity = self._capacities.get(queue_name, self._default_capacity)
            reserved = self._reserved.get(queue_name, 0)
            return max(0, capacity - reserved)
    
    def _reserve(self, queue_name: str, reservation_id: str) -> bool:
        """
        Reserve capacity for a queue.
        
        Args:
            queue_name: Name of the queue
            reservation_id: Unique ID for this reservation
            
        Returns:
            True if reserved, False if capacity exceeded
        """
        with self._lock:
            capacity = self._capacities.get(queue_name, self._default_capacity)
            reserved = self._reserved.get(queue_name, 0)
            
            if reserved >= capacity:
                logger.warning(
                    f"Queue '{queue_name}' capacity exceeded: "
                    f"{reserved}/{capacity} reserved"
                )
                return False
            
            self._reserved[queue_name] = reserved + 1
            import time
            self._reservations[reservation_id] = CapacityReservation(
                queue_name=queue_name,
                reserved_at=time.time()
            )
            logger.debug(f"Reserved capacity for '{queue_name}': {reservation_id}")
            return True
    
    def _release(self, reservation_id: str) -> bool:
        """
        Release reserved capacity.
        
        Args:
            reservation_id: ID of the reservation to release
            
        Returns:
            True if released, False if not found
        """
        with self._lock:
            reservation = self._reservations.get(reservation_id)
            if not reservation:
                return False
            
            if reservation.released:
                logger.warning(f"Double release detected: {reservation_id}")
                return False
            
            queue_name = reservation.queue_name
            reserved = self._reserved.get(queue_name, 0)
            
            if reserved > 0:
                self._reserved[queue_name] = reserved - 1
                reservation.released = True
                logger.debug(f"Released capacity for '{queue_name}': {reservation_id}")
                return True
            
            return False
    
    @contextmanager
    def acquire(self, queue_name: str, reservation_id: Optional[str] = None):
        """
        Context manager for atomic capacity acquisition with automatic release.
        
        Usage:
            with limiter.acquire("my_queue") as reserved:
                if reserved:
                    # Do work, capacity auto-released on exit
                    pass
        """
        import uuid
        rid = reservation_id or str(uuid.uuid4())
        reserved = False
        
        try:
            reserved = self._reserve(queue_name, rid)
            if not reserved:
                raise CapacityExceededError(
                    f"Queue '{queue_name}' has no available capacity"
                )
            yield reserved
        finally:
            if reserved:
                self._release(rid)
    
    def execute_with_capacity(
        self,
        queue_name: str,
        operation: Callable,
        *args,
        **kwargs
    ) -> any:
        """
        Execute an operation with capacity reservation and automatic rollback.
        
        Args:
            queue_name: Queue to reserve capacity in
            operation: Callable to execute
            *args, **kwargs: Arguments for the operation
            
        Returns:
            Result of the operation
            
        Raises:
            CapacityExceededError: If no capacity available
            Exception: Re-raises any exception from operation
        """
        import uuid
        reservation_id = str(uuid.uuid4())
        
        # Reserve capacity
        if not self._reserve(queue_name, reservation_id):
            raise CapacityExceededError(f"No capacity in queue '{queue_name}'")
        
        try:
            # Execute operation
            result = operation(*args, **kwargs)
            logger.info(f"Operation completed in '{queue_name}': {reservation_id}")
            return result
        except Exception as e:
            # Operation failed - capacity will be released in finally
            logger.error(f"Operation failed in '{queue_name}': {e}")
            raise
        finally:
            # Always release capacity, even on failure (rollback)
            self._release(reservation_id)
    
    def get_metrics(self) -> Dict[str, Dict]:
        """Get capacity metrics for all queues."""
        with self._lock:
            metrics = {}
            for queue_name in self._capacities:
                capacity = self._capacities[queue_name]
                reserved = self._reserved.get(queue_name, 0)
                metrics[queue_name] = {
                    "capacity": capacity,
                    "reserved": reserved,
                    "available": capacity - reserved,
                    "utilization": reserved / capacity if capacity > 0 else 0
                }
            return metrics


def create_capacity_limiter(capacity: int = 100) -> QueueCapacityLimiter:
    """Factory function to create a capacity limiter."""
    return QueueCapacityLimiter(default_capacity=capacity)