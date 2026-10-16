"""Tolerance for comparing engine results against Carvalho's printed values.

FROZEN: see the "Source-of-truth tests" section of AGENTS.md.
"""

from tests.helpers import assert_approx

BOOK_RELATIVE_TOLERANCE = 0.005  # 0.5 %, absorbs the book's rounded intermediates


def assert_book_value(
    actual: float, expected: float, message: str, *, decimals: int
) -> None:
    """Assert that a result matches a value printed in the book

    The tolerance is the larger of 0.5 % of the expected value and half a unit
    of its last printed digit, so values printed with few digits are not held
    to more precision than the book shows.

    Args:
        actual: Engine result, already converted to the book's unit.
        expected: Value as printed in the book.
        message: Assertion message describing the expectation and its unit.
        decimals: Number of decimal places the book prints for the value.
    """
    abs_tol = max(BOOK_RELATIVE_TOLERANCE * abs(expected), 0.5 * 10**-decimals)
    assert_approx(actual, expected, message, abs_tol=abs_tol)
