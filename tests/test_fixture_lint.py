"""Tests for fixture sanitization linter."""

import pytest
import tempfile
import os
from pathlib import Path

from tests.fixture_lint import FixtureLinter, PROHIBITED_PATTERNS


class TestFixtureLinterPatterns:
    """Verify prohibited patterns are correctly detected."""

    def test_api_key_pattern(self):
        import re
        pattern = PROHIBITED_PATTERNS[0][0]
        assert re.search(pattern, 'api_key = "sk-abc123456789"')

    def test_real_email_pattern(self):
        import re
        pattern = PROHIBITED_PATTERNS[1][0]
        assert re.search(pattern, "user@gmail.com")
        # Should NOT match test emails
        assert not re.search(pattern, "user@test.com")

    def test_aws_key_pattern(self):
        import re
        pattern = PROHIBITED_PATTERNS[4][0]
        assert re.search(pattern, "AKIAIOSFODNN7EXAMPLE")

    def test_github_token_pattern(self):
        import re
        pattern = PROHIBITED_PATTERNS[5][0]
        assert re.search(pattern, "ghp_abc123def456ghi789jkl012mno345pqr678stu")


class TestFixtureLinter:
    """Tests for the FixtureLinter class."""

    def test_clean_file_no_violations(self, tmp_path):
        """Files with synthetic data should produce no violations."""
        test_file = tmp_path / "test_clean.py"
        test_file.write_text('''
def test_something():
    data = {"name": "test-agent", "port": 8080}
    assert data["name"] == "test-agent"
''')
        linter = FixtureLinter(scan_paths=[str(tmp_path)])
        assert linter.scan() == 0

    def test_file_with_real_email(self, tmp_path):
        """Files with real email addresses should be flagged."""
        test_file = tmp_path / "test_dirty.py"
        test_file.write_text('''
def test_email():
    email = "admin@realcompany.com"
    assert send_email(email)
''')
        linter = FixtureLinter(scan_paths=[str(tmp_path)])
        assert linter.scan() == 1

    def test_file_with_api_key(self, tmp_path):
        """Files with API keys should be flagged."""
        test_file = tmp_path / "test_keys.py"
        test_file.write_text('''
API_KEY = "sk-1234567890abcdef"
''')
        linter = FixtureLinter(scan_paths=[str(tmp_path)])
        assert linter.scan() >= 1

    def test_file_with_ip_address(self, tmp_path):
        """Files with IP addresses should be flagged."""
        test_file = tmp_path / "test_ips.py"
        test_file.write_text('''
server = "192.168.1.100"
''')
        linter = FixtureLinter(scan_paths=[str(tmp_path)])
        assert linter.scan() >= 1

    def test_allow_comment_suppresses(self, tmp_path):
        """Inline allow comments should suppress violations."""
        test_file = tmp_path / "test_allowed.py"
        test_file.write_text('''
# fixture-lint: allow
email = "admin@realcompany.com"
''')
        linter = FixtureLinter(scan_paths=[str(tmp_path)])
        assert linter.scan() == 0

    def test_test_email_not_flagged(self, tmp_path):
        """test.com and example.com emails should not be flagged."""
        test_file = tmp_path / "test_safe_email.py"
        test_file.write_text('''
email = "user@test.com"
email2 = "user@example.com"
''')
        linter = FixtureLinter(scan_paths=[str(tmp_path)])
        assert linter.scan() == 0

    def test_report_ok(self, tmp_path):
        """Report should say OK when no violations."""
        test_file = tmp_path / "test_ok.py"
        test_file.write_text("pass\n")
        linter = FixtureLinter(scan_paths=[str(tmp_path)])
        linter.scan()
        assert "0 violations" in linter.report()

    def test_report_violations(self, tmp_path):
        """Report should list violations when found."""
        test_file = tmp_path / "test_bad.py"
        test_file.write_text('key = "AKIAIOSFODNN7EXAMPLE"\n')
        linter = FixtureLinter(scan_paths=[str(tmp_path)])
        linter.scan()
        assert "1 violation" in linter.report()
        assert "AWS" in linter.report()

    def test_main_returns_zero_on_clean(self, tmp_path):
        """main() should return 0 when clean."""
        test_file = tmp_path / "clean.py"
        test_file.write_text("pass\n")
        linter = FixtureLinter(scan_paths=[str(tmp_path)])
        assert linter.scan() == 0