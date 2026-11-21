"""Errors the engine raises by its own rules, one module per group

Every class derives from ``BeamCalculatorError`` and also from the builtin the
engine raised before it existed (``ValueError``, ``KeyError``, ``RuntimeError``),
so code that catches the builtin keeps working. Catch the specific class to react
to one failure, e.g. raise the section after a failed deflection check.
"""

from src.errors.base import BeamCalculatorError
from src.errors.design import BeamDesignError, DesignError, SlabDesignError
from src.errors.detailing import BeamDetailingError, DetailingError
from src.errors.drawing import DrawingError, DxfAuditError, SheetFitError
from src.errors.input import InputError
from src.errors.precondition import EnginePreconditionError

__all__ = [
    "BeamCalculatorError",
    "BeamDesignError",
    "BeamDetailingError",
    "DesignError",
    "DetailingError",
    "DrawingError",
    "DxfAuditError",
    "EnginePreconditionError",
    "InputError",
    "SheetFitError",
    "SlabDesignError",
]
