"""Tests for src/errors/file.py."""

from src.errors.file import MalformedFileError
from src.errors.input import InputError


class TestMalformedFileError:
    """A malformed file error adds the common prefix to its detail."""

    def test_message_and_detail(self) -> None:
        error = MalformedFileError("missing 'beams' in Document")
        assert isinstance(error, InputError), "it is an input error"
        assert str(error) == "malformed pavement file: missing 'beams' in Document", (
            "the text should match the engine's message"
        )
        assert error.detail == "missing 'beams' in Document", (
            "the detail should be kept without the prefix"
        )
