"""Tests for src/errors/drawing.py."""

from src.errors.base import BeamCalculatorError
from src.errors.drawing import DrawingError, DxfAuditError, SheetFitError


class TestDrawingErrors:
    """The drawing errors are engine errors still caught as their builtins."""

    def test_drawing_error(self) -> None:
        assert issubclass(DrawingError, BeamCalculatorError), (
            "DrawingError should derive from BeamCalculatorError"
        )
        assert issubclass(DrawingError, ValueError), (
            "DrawingError should still be caught as ValueError"
        )

    def test_sheet_fit_is_a_drawing_error(self) -> None:
        assert issubclass(SheetFitError, DrawingError), (
            "a sheet that does not fit is a drawing error"
        )

    def test_dxf_audit_error(self) -> None:
        assert issubclass(DxfAuditError, BeamCalculatorError), (
            "DxfAuditError should derive from BeamCalculatorError"
        )
        assert issubclass(DxfAuditError, RuntimeError), (
            "DxfAuditError should still be caught as RuntimeError"
        )
