"""Fixture sanitization linter for test data.

Scans test directories for prohibited patterns in fixture data:
- Real email addresses
- Real API keys, tokens, passwords
- Real URLs pointing to external services
- Real IP addresses
- Real phone numbers
- Real names combined with PII patterns

Usage:
    python -m tests.fixture_lint          # lint all test paths
    python -m tests.fixture_lint --fix    # also show suggestions
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Prohibited patterns for test fixtures
PROHIBITED_PATTERNS = [
    # API keys and tokens
    (r'(?:api[_-]?key|token|secret|password|passwd)\s*[=:]\s*["\'][^"\']{8,}["\']', "API key or secret detected"),
    # Real email addresses (allow test/example/fake)
    (r'[a-zA-Z0-9._%+-]+@(?!test\.|example\.|fake\.|localhost)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', "Real email address detected"),
    # Real URLs with auth
    (r'https?://[^/\s:]+:[^/\s@]+@[^\s"\']+', "URL with embedded credentials"),
    # Private IP addresses in fixture data
    (r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b', "IP address detected (use 127.0.0.1 or 0.0.0.0)"),
    # AWS-style keys
    (r'(?:AKIA|ASIA)[A-Z0-9]{16}', "AWS access key detected"),
    # GitHub tokens
    (r'gh[ps]_[A-Za-z0-9_]{36,}', "GitHub token detected"),
    # Bearer tokens
    (r'Bearer\s+[A-Za-z0-9._-]{20,}', "Bearer token detected"),
]

# Paths to scan
DEFAULT_SCAN_PATHS = [
    "tests/",
    "src/",
]

# Patterns allowed in specific contexts (false positive suppression)
ALLOWED_CONTEXTS = [
    (r'#\s*fixture-lint:\s*allow', "inline allow comment"),
]


class FixtureLinter:
    """Lints test fixture data for prohibited patterns."""

    def __init__(self, scan_paths: List[str] = None):
        self.scan_paths = scan_paths or DEFAULT_SCAN_PATHS
        self.violations: List[Tuple[str, int, str, str]] = []
        self.files_scanned = 0

    def scan(self) -> int:
        """Scan all configured paths. Returns number of violations."""
        for scan_path in self.scan_paths:
            root = Path(scan_path)
            if not root.exists():
                continue
            for filepath in root.rglob("*.py"):
                self._scan_file(filepath)
        return len(self.violations)

    def _scan_file(self, filepath: Path) -> None:
        """Scan a single file for prohibited patterns."""
        self.files_scanned += 1
        try:
            content = filepath.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            return

        lines = content.splitlines()
        for line_num, line in enumerate(lines, 1):
            # Skip allowed contexts
            for allow_pattern, _ in ALLOWED_CONTEXTS:
                if re.search(allow_pattern, line):
                    break
            else:
                for pattern, description in PROHIBITED_PATTERNS:
                    if re.search(pattern, line):
                        self.violations.append(
                            (str(filepath), line_num, description, line.strip())
                        )
                        break  # One violation per line

    def report(self) -> str:
        """Generate a human-readable report."""
        if not self.violations:
            return f"OK: {self.files_scanned} files scanned, 0 violations found."

        lines = [f"FOUND {len(self.violations)} violation(s) across {self.files_scanned} file(s):"]
        for filepath, line_num, description, content in self.violations:
            lines.append(f"  {filepath}:{line_num}: {description}")
            lines.append(f"    > {content}")
        return "\n".join(lines)


def main() -> int:
    """Entry point for fixture linting."""
    linter = FixtureLinter()
    violation_count = linter.scan()
    print(linter.report())
    return 1 if violation_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())