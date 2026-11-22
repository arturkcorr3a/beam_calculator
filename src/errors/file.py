"""Errors for pavement files that cannot be read"""

from src.errors.input import InputError


class MalformedFileError(InputError):
    """A pavement file does not have the expected content

    Attributes:
        detail: What is wrong, after the common "malformed pavement file: " prefix.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(f"malformed pavement file: {detail}")
        self.detail = detail
