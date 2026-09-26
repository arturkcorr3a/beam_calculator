"""Shared assertion helpers for the properties test suite."""

import pytest


def assert_approx(
    actual: float,
    expected: float,
    message: str,
    *,
    abs_tol: float = 1e-5,
) -> None:
    """Assert that a float equals an expected value within an absolute tolerance.

    Wraps ``pytest.approx`` so the single unavoidable type suppression lives here
    instead of at every call site.

    Args:
        actual: Value produced by the code under test.
        expected: Hardcoded reference value.
        message: Assertion message describing the expectation and its physical unit.
        abs_tol: Absolute tolerance for the comparison. Defaults to 1e-5 so that
            reference values hardcoded to 5-decimal precision compare cleanly.
    """
    assert actual == pytest.approx(expected, abs=abs_tol), message  # type: ignore[reportUnknownMemberType]
