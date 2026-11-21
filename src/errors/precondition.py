"""Errors for engine objects used out of order"""

from src.errors.base import BeamCalculatorError


class EnginePreconditionError(BeamCalculatorError, ValueError):
    """An engine object was used before the step it depends on, or with arguments it never accepts

    It signals a bug in the calling code, not a property of the structure.
    """
