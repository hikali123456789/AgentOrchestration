"""Tests for scheduler lease renewer."""

import pytest
import time
from src.orchestrator.lease import (
    LeaseRenewer, Lease, LeaseState, LeaseRenewalError
)


class TestLeaseAcquisition:
    """Tests for lease acquisition."""

    def test_acquire_lease(self):
        renewer = LeaseRenewer()
        lease = renewer.acquire_lease("resource1", "owner1", "lease1")
        assert lease.id == "lease1"
        assert lease.resource_id == "resource1"
        assert lease.state == LeaseState.ACTIVE

    def test_acquire_duplicate_fails(self):
        renewer = LeaseRenewer()
        renewer.acquire_lease("resource1", "owner1", "lease1")
        with pytest.raises(LeaseRenewalError):
            renewer.acquire_lease("resource1", "owner2", "lease2")


class TestLeaseRenewal:
    """Tests for lease renewal."""

    def test_renew_active_lease(self):
        renewer = LeaseRenewer()
        lease = renewer.acquire_lease("resource1", "owner1", "lease1")
        success = renewer.renew_lease("lease1")
        assert success is True
        assert lease.renewed_at is not None

    def test_renew_nonexistent_lease(self):
        renewer = LeaseRenewer()
        success = renewer.renew_lease("nonexistent")
        assert success is False

    def test_renew_expired_lease_fails(self):
        renewer = LeaseRenewer()
        lease = renewer.acquire_lease("resource1", "owner1", "lease1")
        lease.state = LeaseState.EXPIRED
        success = renewer.renew_lease("lease1")
        assert success is False


class TestTransientErrorRecovery:
    """Tests for transient error handling."""

    def test_resume_after_failure(self):
        renewer = LeaseRenewer()
        lease = renewer.acquire_lease("resource1", "owner1", "lease1")
        
        # Simulate failure
        lease.state = LeaseState.FAILED
        lease.renewal_failures = 3
        
        success = renewer.resume_after_transient_error("lease1")
        assert success is True
        assert lease.state == LeaseState.ACTIVE
        assert lease.renewal_failures == 0

    def test_resume_not_in_failed_state(self):
        renewer = LeaseRenewer()
        lease = renewer.acquire_lease("resource1", "owner1", "lease1")
        
        # Lease is ACTIVE, not FAILED
        success = renewer.resume_after_transient_error("lease1")
        assert success is False

    def test_resume_expired_lease_fails(self):
        renewer = LeaseRenewer()
        lease = renewer.acquire_lease("resource1", "owner1", "lease1")
        
        lease.state = LeaseState.FAILED
        lease.expires_at = time.time() - 1  # Expired
        
        success = renewer.resume_after_transient_error("lease1")
        assert success is False
        assert lease.state == LeaseState.EXPIRED


class TestLeaseRelease:
    """Tests for lease release."""

    def test_release_lease(self):
        renewer = LeaseRenewer()
        renewer.acquire_lease("resource1", "owner1", "lease1")
        success = renewer.release_lease("lease1")
        assert success is True
        
        lease = renewer.get_lease("lease1")
        assert lease.state == LeaseState.EXPIRED

    def test_release_nonexistent(self):
        renewer = LeaseRenewer()
        success = renewer.release_lease("nonexistent")
        assert success is False


class TestAuditLogging:
    """Tests for audit logging."""

    def test_audit_log_added(self):
        renewer = LeaseRenewer()
        lease = renewer.acquire_lease("resource1", "owner1", "lease1")
        assert len(lease.audit_log) > 0
        assert lease.audit_log[0]["action"] == "ACQUIRED"

    def test_audit_log_bounded(self):
        renewer = LeaseRenewer()
        lease = renewer.acquire_lease("resource1", "owner1", "lease1")
        
        # Add many records
        for i in range(150):
            lease.audit_log.append({"timestamp": time.time(), "action": f"TEST{i}"})
        
        renewer._add_audit_record(lease, "BOUNDARY", "test")
        assert len(lease.audit_log) <= 100


class TestMetrics:
    """Tests for metrics."""

    def test_get_metrics(self):
        renewer = LeaseRenewer()
        renewer.acquire_lease("r1", "o1", "l1")
        renewer.acquire_lease("r2", "o2", "l2")
        
        metrics = renewer.get_metrics()
        assert metrics["total_leases"] == 2
        assert metrics["active"] == 2

    def test_metrics_with_failed(self):
        renewer = LeaseRenewer()
        lease = renewer.acquire_lease("r1", "o1", "l1")
        lease.state = LeaseState.FAILED
        
        metrics = renewer.get_metrics()
        assert metrics["failed"] == 1
        assert metrics["active"] == 0