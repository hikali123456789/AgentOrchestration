"""Tests for CLI deploy exit code propagation."""

import pytest
import sys
from unittest.mock import patch

from src.cli.main import cli, handle_init, handle_deploy, handle_status, handle_logs, EXIT_SUCCESS, EXIT_FAILURE


class TestExitCodes:
    """Tests for explicit exit code constants."""

    def test_exit_success_is_zero(self):
        assert EXIT_SUCCESS == 0

    def test_exit_failure_is_one(self):
        assert EXIT_FAILURE == 1


class TestCommandHandlers:
    """Tests for individual command handlers returning exit codes."""

    def test_handle_init_returns_success(self):
        args = type("Args", (), {"name": "test-project"})()
        assert handle_init(args) == EXIT_SUCCESS

    def test_handle_deploy_returns_success(self):
        args = type("Args", (), {"manifest": "manifest.yaml"})()
        assert handle_deploy(args) == EXIT_SUCCESS

    def test_handle_status_returns_success(self):
        args = type("Args", (), {"watch": False})()
        assert handle_status(args) == EXIT_SUCCESS

    def test_handle_logs_returns_success(self):
        args = type("Args", (), {"agent_id": "agent123", "tail": 50})()
        assert handle_logs(args) == EXIT_SUCCESS


class TestCliReturnCodes:
    """Tests for cli() returning proper exit codes."""

    def test_no_command_returns_failure(self):
        with patch.object(sys, "argv", ["cli"]):
            assert cli() == EXIT_FAILURE

    def test_init_command_returns_success(self):
        with patch.object(sys, "argv", ["cli", "init", "myproject"]):
            assert cli() == EXIT_SUCCESS

    def test_deploy_command_returns_success(self):
        with patch.object(sys, "argv", ["cli", "deploy", "manifest.yaml"]):
            assert cli() == EXIT_SUCCESS

    def test_status_command_returns_success(self):
        with patch.object(sys, "argv", ["cli", "status"]):
            assert cli() == EXIT_SUCCESS

    def test_logs_command_returns_success(self):
        with patch.object(sys, "argv", ["cli", "logs", "agent123"]):
            assert cli() == EXIT_SUCCESS

    def test_logs_negative_tail_returns_failure(self):
        with patch.object(sys, "argv", ["cli", "logs", "agent123", "--tail", "-5"]):
            with pytest.raises(SystemExit) as exc_info:
                cli()
            assert exc_info.value.code == 2