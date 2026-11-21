"""Errors for drawings and their files"""

from src.errors.base import BeamCalculatorError


class DrawingError(BeamCalculatorError, ValueError):
    """The beam or pavement cannot be drawn as it is"""


class SheetFitError(DrawingError):
    """The drawing does not fit in the requested sheet"""


class DxfAuditError(BeamCalculatorError, RuntimeError):
    """The DXF document failed ezdxf's audit"""
