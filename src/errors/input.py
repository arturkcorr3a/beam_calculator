"""Errors for the data that describes the structure"""

from src.errors.base import BeamCalculatorError


class InputError(BeamCalculatorError, ValueError):
    """The data that describes the structure is refused by a rule"""
