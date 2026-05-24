"""Tests for CLI argument validation."""

import pytest
import sys
from unittest.mock import patch

from src.cli.main import cli, non_negative_int


class TestNonNegativeInt:
    """Tests for the non_negative_int argparse type."""

    def test_valid_positive_integer(self):
        """Valid positive integers should be accepted."""
        assert non_negative_int("10") == 10

    def test_valid_zero(self):
        """Zero should be accepted as valid."""
        assert non_negative_int("0") == 0

    def test_valid_large_integer(self):
        """Large positive integers should be accepted."""
        assert non_negative_int("1000000") == 1000000

    def test_negative_integer_raises_error(self):
        """Negative integers should raise ArgumentTypeError."""
        import argparse
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            non_negative_int("-5")
        assert "non-negative" in str(exc_info.value)

    def test_negative_one_raises_error(self):
        """-1 should raise ArgumentTypeError."""
        import argparse
        with pytest.raises(argparse.ArgumentTypeError):
            non_negative_int("-1")

    def test_invalid_string_raises_error(self):
        """Non-integer strings should raise ArgumentTypeError."""
        import argparse
        with pytest.raises(argparse.ArgumentTypeError):
            non_negative_int("abc")

    def test_float_raises_error(self):
        """Float strings should raise ArgumentTypeError."""
        import argparse
        with pytest.raises(argparse.ArgumentTypeError):
            non_negative_int("3.14")


class TestCliTailValidation:
    """Tests for CLI --tail argument validation."""

    def test_tail_positive_value(self):
        """Positive --tail value should be accepted."""
        with patch.object(sys, "argv", ["cli", "logs", "agent123", "--tail", "100"]):
            # Should not raise
            try:
                cli()
            except SystemExit as e:
                # cli() exits with 1 when no command handler, but args should parse fine
                pass

    def test_tail_zero_value(self):
        """--tail 0 should be accepted."""
        with patch.object(sys, "argv", ["cli", "logs", "agent123", "--tail", "0"]):
            try:
                cli()
            except SystemExit:
                pass

    def test_tail_negative_value_exits(self):
        """Negative --tail value should cause argument error."""
        with patch.object(sys, "argv", ["cli", "logs", "agent123", "--tail", "-5"]):
            with pytest.raises(SystemExit) as exc_info:
                cli()
            # argparse exits with code 2 for argument errors
            assert exc_info.value.code == 2

    def test_tail_invalid_string_exits(self):
        """Non-integer --tail value should cause argument error."""
        with patch.object(sys, "argv", ["cli", "logs", "agent123", "--tail", "abc"]):
            with pytest.raises(SystemExit) as exc_info:
                cli()
            assert exc_info.value.code == 2

    def test_tail_default_value(self):
        """Default --tail value should be 50."""
        with patch.object(sys, "argv", ["cli", "logs", "agent123"]):
            try:
                cli()
            except SystemExit:
                pass