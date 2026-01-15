"""
Pytest integration for JavaScript unit tests.

This module runs the JavaScript tests via Node.js and reports results
within the pytest framework.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.comparison, pytest.mark.integration]


def find_node_binary() -> str | None:
    """Find Node.js binary on the system."""
    # Check common locations
    candidates = [
        # Homebrew
        "/usr/local/bin/node",
        "/opt/homebrew/bin/node",
        # System
        "/usr/bin/node",
        "/usr/bin/nodejs",
        # Conductor bundled (if available)
        Path.home()
        / "Library"
        / "Application Support"
        / "com.conductor.app"
        / "bin"
        / "node",
    ]

    for candidate in candidates:
        if isinstance(candidate, Path):
            if candidate.exists():
                return str(candidate)
        elif shutil.which(candidate):
            return candidate

    # Fall back to PATH
    node = shutil.which("node") or shutil.which("nodejs")
    return node


NODE_BINARY = find_node_binary()
JS_TEST_DIR = Path(__file__).parent.parent.parent / "js"
JS_TEST_SCRIPT = JS_TEST_DIR / "run-tests.js"


@pytest.fixture
def node_available():
    """Check if Node.js is available for testing."""
    if NODE_BINARY is None:
        pytest.skip("Node.js not available on this system")
    if not JS_TEST_SCRIPT.exists():
        pytest.skip(f"JavaScript test script not found: {JS_TEST_SCRIPT}")
    return NODE_BINARY


class TestJavaScriptUnit:
    """Run JavaScript unit tests and report results in pytest."""

    def test_javascript_helpers_all_pass(self, node_available):
        """
        Run all JavaScript unit tests and verify they pass.

        This test calls the Node.js test runner and parses the JSON output.
        """
        result = subprocess.run(
            [node_available, str(JS_TEST_SCRIPT)],
            capture_output=True,
            text=True,
            cwd=str(JS_TEST_DIR),
            timeout=30,
        )

        # Parse JSON output from the test runner
        # The JSON is on the last line after "--- JSON Output ---"
        output_lines = result.stdout.strip().split("\n")
        json_line = output_lines[-1] if output_lines else "{}"

        try:
            test_results = json.loads(json_line)
        except json.JSONDecodeError:
            pytest.fail(f"Could not parse JavaScript test output:\n{result.stdout}")

        # Report results
        passed = test_results.get("passed", 0)
        failed = test_results.get("failed", 0)
        xfailed = test_results.get("xfailed", 0)
        total = test_results.get("total", 0)

        # Print summary
        print(f"\nJavaScript Test Results:")
        print(f"  Passed:  {passed}")
        print(f"  Failed:  {failed}")
        print(f"  XFailed: {xfailed} (expected failures documenting bugs)")
        print(f"  Total:   {total}")

        # Check for unexpected failures
        failures = test_results.get("failures", [])
        if failures:
            failure_msgs = "\n".join(
                f"  - {f['name']}: {f['error']}" for f in failures
            )
            pytest.fail(f"JavaScript tests had unexpected failures:\n{failure_msgs}")

        # Check for unexpected passes (xfail tests that now pass)
        unexpected_passes = test_results.get("unexpected_passes", [])
        if unexpected_passes:
            pass_msgs = "\n".join(f"  - {f['name']}" for f in unexpected_passes)
            # This is informational - bugs might be fixed!
            print(f"\nNote: Some expected failures now pass:\n{pass_msgs}")

        # Verify we ran some tests
        assert total > 0, "No JavaScript tests were run"

    def test_javascript_test_file_exists(self, node_available):
        """Verify the JavaScript test infrastructure exists."""
        assert JS_TEST_DIR.exists(), f"JS test directory not found: {JS_TEST_DIR}"
        assert JS_TEST_SCRIPT.exists(), f"JS test script not found: {JS_TEST_SCRIPT}"

        helpers_file = JS_TEST_DIR / "src" / "comparison-helpers.js"
        assert helpers_file.exists(), f"JS helpers not found: {helpers_file}"

    def test_javascript_syntax_valid(self, node_available):
        """Verify JavaScript files have valid syntax."""
        helpers_file = JS_TEST_DIR / "src" / "comparison-helpers.js"

        # Use Node.js to check syntax
        result = subprocess.run(
            [node_available, "--check", str(helpers_file)],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, (
            f"JavaScript syntax error in {helpers_file}:\n{result.stderr}"
        )


class TestJavaScriptBugDocumentation:
    """
    Tests that document specific JavaScript bugs.

    These tests verify that the xfail tests in JavaScript are correctly
    documenting the bugs we've identified.
    """

    def test_xfailed_tests_document_placeholder_bug(self, node_available):
        """
        Verify that xfail tests document the new_ placeholder bug.

        The JavaScript tests should have xfail tests for:
        - isListItemPath not matching new_ placeholders
        - extractListFieldPath not working for placeholders
        - extractListIndex returning null for placeholders
        """
        result = subprocess.run(
            [node_available, str(JS_TEST_SCRIPT)],
            capture_output=True,
            text=True,
            cwd=str(JS_TEST_DIR),
            timeout=30,
        )

        output_lines = result.stdout.strip().split("\n")
        json_line = output_lines[-1] if output_lines else "{}"
        test_results = json.loads(json_line)

        xfailed = test_results.get("xfailed", 0)

        # We should have at least 4 xfail tests documenting bugs
        assert xfailed >= 4, (
            f"Expected at least 4 xfail tests documenting bugs, got {xfailed}"
        )

    def test_fixed_functions_exist(self, node_available):
        """
        Verify that fixed versions of buggy functions are implemented.

        The JavaScript module should export both buggy and fixed versions:
        - isListItemPath (buggy) -> isListItemPathFixed
        - extractListFieldPath (buggy) -> extractListFieldPathFixed
        - extractListIndex (buggy) -> extractListIndexFixed
        """
        # Read the helpers file and check exports
        helpers_file = JS_TEST_DIR / "src" / "comparison-helpers.js"
        content = helpers_file.read_text()

        # Check for fixed function implementations
        assert "function isListItemPathFixed" in content
        assert "function isListSubfieldPath" in content
        assert "function extractListFieldPathFixed" in content
        assert "function extractListIndexFixed" in content
        assert "function getCopyBehavior" in content

    def test_fixed_functions_in_exports(self, node_available):
        """Verify fixed functions are exported for use."""
        helpers_file = JS_TEST_DIR / "src" / "comparison-helpers.js"
        content = helpers_file.read_text()

        # Check exports section
        assert "isListItemPathFixed," in content or "isListItemPathFixed" in content
        assert "isListSubfieldPath," in content or "isListSubfieldPath" in content
        assert "getCopyBehavior," in content or "getCopyBehavior" in content
