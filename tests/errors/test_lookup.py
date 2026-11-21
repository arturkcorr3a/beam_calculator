"""Tests for src/errors/lookup.py."""

from src.errors.input import InputError
from src.errors.lookup import SteelPriceNotFoundError, TableLookupError


class TestTableLookupError:
    """A table lookup error is caught both as KeyError and as ValueError."""

    def test_hierarchy(self) -> None:
        assert issubclass(TableLookupError, InputError), "it is an input error"
        assert issubclass(TableLookupError, KeyError), (
            "it should still be caught as KeyError (NBR 6120 lookups)"
        )
        assert issubclass(TableLookupError, ValueError), (
            "it should still be caught as ValueError (thickness lookups)"
        )

    def test_text_is_not_quoted(self) -> None:
        error = TableLookupError(
            "No material matching 'x' was found.",
            table="ABNT NBR 6120:2019 — Table 7",
            value="x",
        )
        assert str(error) == "No material matching 'x' was found.", (
            "unlike KeyError, the text should not be wrapped in quotes"
        )
        assert error.table == "ABNT NBR 6120:2019 — Table 7", "the table is kept"
        assert error.value == "x", "the value looked up is kept"


class TestSteelPriceNotFoundError:
    """A missing SINAPI price keeps the bar it was asked for."""

    def test_message_and_fields(self) -> None:
        error = SteelPriceNotFoundError(steel="CA60", diameter_mm=12.5)
        assert isinstance(error, TableLookupError), "it is a table lookup"
        assert str(error) == "No SINAPI price for CA60 φ12.5 mm.", (
            "the text should match the engine's message"
        )
        assert error.diameter_mm == 12.5, "the diameter is kept (mm)"
