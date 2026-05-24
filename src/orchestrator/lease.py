"""Scheduler lease renewer with transient error handling."""

import logging
import threading
import time
from typing import Dict, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class LeaseState(Enum):
    """Lease lifecycle states."""
    PENDING = "pending"
    ACTIVE = "active"
    RENEWING = "renewing"
    EXPIRED = "expired"
    FAILED = "failed"


@dataclass
class Lease:
    """Represents a scheduler lease."""
    id: str
    resource_id: str
    owner: str
    state: LeaseState = LeaseState.PENDING
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 30)
    renewed_at: Optional[float] = None
    renewal_failures: int = 0
    max_renewal_failures: int = 3
    audit_log: list = field(default_factory=list)


class LeaseRenewalError(Exception):
    """Raised when lease renewal fails."""
    pass


class LeaseRenewer:
    """
    Scheduler lease renewer with atomic state preconditions.
    
    Handles lease renewal failures gracefully, ensuring leases are
    resumed correctly after transient store errors without causing
    duplicate runs or policy violations.
    """
    
    def __init__(
        self,
        renewal_interval: float = 10.0,
        lease_duration: float = 30.0,
        max_failures: int = 3
    ):
        self.renewal_interval = renewal_interval
        self.lease_duration = lease_duration
        self.max_failures = max_failures
        self._leases: Dict[str, Lease] = {}
        self._lock = threading.RLock()
        self._running = False
        self._renewal_thread: Optional[threading.Thread] = None
    
    def acquire_lease(self, resource_id: str, owner: str, lease_id: str) -> Lease:
        """
        Acquire a new lease with atomic state precondition.
        
        Args:
            resource_id: Resource to lease
            owner: Lease owner identifier
            lease_id: Unique lease identifier
            
        Returns:
            Acquired Lease
        """
        with self._lock:
            # Check for existing lease
            if resource_id in self._leases:
                existing = self._leases[resource_id]
                if existing.state not in (LeaseState.EXPIRED, LeaseState.FAILED):
                    raise LeaseRenewalError(
                        f"Resource {resource_id} already has active lease {existing.id}"
                    )
            
            lease = Lease(
                id=lease_id,
                resource_id=resource_id,
                owner=owner,
                state=LeaseState.ACTIVE,
                expires_at=time.time() + self.lease_duration,
                max_renewal_failures=self.max_failures
            )
            
            self._leases[lease_id] = lease
            self._add_audit_record(lease, "ACQUIRED", f"Owner: {owner}")
            
            logger.info(f"Lease acquired: {lease_id} for {resource_id}")
            return lease
    
    def _add_audit_record(self, lease: Lease, action: str, details: str = "") -> None:
        """Add bounded audit record to lease."""
        record = {
            "timestamp": time.time(),
            "action": action,
            "state": lease.state.value,
            "details": details
        }
        lease.audit_log.append(record)
        # Keep only last 100 records (bounded)
        if len(lease.audit_log) > 100:
            lease.audit_log = lease.audit_log[-100:]
    
    def renew_lease(self, lease_id: str) -> bool:
        """
        Renew a lease with atomic state precondition.
        
        Args:
            lease_id: Lease to renew
            
        Returns:
            True if renewed, False if failed
        """
        with self._lock:
            lease = self._leases.get(lease_id)
            if not lease:
                logger.error(f"Lease not found: {lease_id}")
                return False
            
            # Atomic state precondition
            if lease.state not in (LeaseState.ACTIVE, LeaseState.RENEWING):
                logger.warning(
                    f"Cannot renew lease {lease_id} in state {lease.state.value}"
                )
                return False
            
            # Store previous state for rollback
            previous_state = lease.state
            lease.state = LeaseState.RENEWING
            
            try:
                # Attempt renewal (simulated store operation)
                self._persist_renewal(lease)
                
                # Success - update lease
                lease.renewed_at = time.time()
                lease.expires_at = time.time() + self.lease_duration
                lease.renewal_failures = 0
                lease.state = LeaseState.ACTIVE
                
                self._add_audit_record(lease, "RENEWED", f"Expires: {lease.expires_at}")
                logger.info(f"Lease renewed: {lease_id}")
                return True
                
            except Exception as e:
                # Renewal failed - handle gracefully
                lease.renewal_failures += 1
                lease.state = previous_state  # Rollback state
                
                self._add_audit_record(
                    lease, "RENEWAL_FAILED", f"Failure #{lease.renewal_failures}: {e}"
                )
                
                logger.error(
                    f"Lease renewal failed: {lease_id} "
                    f"(failure {lease.renewal_failures}/{self.max_failures})"
                )
                
                # Check if max failures exceeded
                if lease.renewal_failures >= self.max_failures:
                    lease.state = LeaseState.FAILED
                    self._add_audit_record(lease, "MAX_FAILURES", "Lease marked as failed")
                    logger.error(f"Lease {lease_id} exceeded max renewal failures")
                
                return False
    
    def _persist_renewal(self, lease: Lease) -> None:
        """
        Persist lease renewal to store.
        
        Raises:
            Exception: Simulated store error
        """
        # In real implementation, this would write to a durable store
        # For now, simulate occasional transient errors
        import random
        if random.random() < 0.1:  # 10% failure rate for testing
            raise Exception("Simulated store error")
    
    def resume_after_transient_error(self, lease_id: str) -> bool:
        """
        Resume lease after transient store error.
        
        Args:
            lease_id: Lease to resume
            
        Returns:
            True if resumed successfully
        """
        with self._lock:
            lease = self._leases.get(lease_id)
            if not lease:
                return False
            
            # Only resume if state allows
            if lease.state != LeaseState.FAILED:
                logger.warning(f"Lease {lease_id} not in FAILED state, cannot resume")
                return False
            
            # Check if lease is still valid (not expired)
            if time.time() > lease.expires_at:
                logger.error(f"Lease {lease_id} expired, cannot resume")
                lease.state = LeaseState.EXPIRED
                return False
            
            # Resume lease
            lease.state = LeaseState.ACTIVE
            lease.renewal_failures = 0
            self._add_audit_record(lease, "RESUMED", "After transient error")
            
            logger.info(f"Lease resumed after transient error: {lease_id}")
            return True
    
    def release_lease(self, lease_id: str) -> bool:
        """Release a lease."""
        with self._lock:
            lease = self._leases.get(lease_id)
            if not lease:
                return False
            
            lease.state = LeaseState.EXPIRED
            self._add_audit_record(lease, "RELEASED", "Normal release")
            logger.info(f"Lease released: {lease_id}")
            return True
    
    def get_lease(self, lease_id: str) -> Optional[Lease]:
        """Get lease by ID."""
        with self._lock:
            return self._leases.get(lease_id)
    
    def get_metrics(self) -> Dict:
        """Get lease metrics."""
        with self._lock:
            total = len(self._leases)
            active = sum(1 for l in self._leases.values() if l.state == LeaseState.ACTIVE)
            failed = sum(1 for l in self._leases.values() if l.state == LeaseState.FAILED)
            expired = sum(1 for l in self._leases.values() if l.state == LeaseState.EXPIRED)
            
            return {
                "total_leases": total,
                "active": active,
                "failed": failed,
                "expired": expired,
                "renewal_failures": sum(l.renewal_failures for l in self._leases.values())
            }