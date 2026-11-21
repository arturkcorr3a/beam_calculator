"""Errors the engine raises by its own rules, one module per group

Every class derives from ``BeamCalculatorError`` and also from the builtin the
engine raised before it existed (``ValueError``, ``KeyError``, ``RuntimeError``),
so code that catches the builtin keeps working. Catch the specific class to react
to one failure, e.g. raise the section after a failed deflection check.
"""

from src.errors.anchorage import (
    AnchorageError,
    AnchorageLengthError,
    ClampsDoNotFitError,
    HookDoesNotFitError,
    SupportBarsShortError,
)
from src.errors.base import BeamCalculatorError
from src.errors.design import (
    BeamDesignError,
    DeformationLimitExceededError,
    DesignError,
    EffectiveDepthDivergedError,
    MaxLayersExceededError,
    NoReinforcementLayoutError,
    NoStirrupLayoutError,
    ReinforcementAreaExceededError,
    SkinReinforcementNoRoomError,
    SlabDesignError,
    SlabPreSizingDivergedError,
    SlabThicknessExceededError,
    StrutCrushingError,
)
from src.errors.detailing import (
    BeamDetailingError,
    BendPinUndefinedError,
    DetailingError,
    LapTooLongError,
    SpliceDiameterError,
    SplicePositionError,
    StirrupBendUndefinedError,
    StirrupSpacingTooSmallError,
)
from src.errors.drawing import DrawingError, DxfAuditError, SheetFitError
from src.errors.file import MalformedFileError
from src.errors.input import (
    BeamInputError,
    BeamTooNarrowError,
    ConcreteClassTooLowError,
    DuplicateElementError,
    InputError,
    MaterialError,
    PillarInputError,
    PillarTooSmallError,
    SkinSteelError,
    SlabInputError,
    SlabLoweredTooMuchError,
    UnknownPillarError,
)
from src.errors.lookup import SteelPriceNotFoundError, TableLookupError
from src.errors.precondition import (
    EnginePreconditionError,
    NumericalError,
    UnknownNameError,
)

__all__ = [
    "AnchorageError",
    "AnchorageLengthError",
    "BeamCalculatorError",
    "BeamDesignError",
    "BeamDetailingError",
    "BeamInputError",
    "BeamTooNarrowError",
    "BendPinUndefinedError",
    "ClampsDoNotFitError",
    "ConcreteClassTooLowError",
    "DeformationLimitExceededError",
    "DesignError",
    "DetailingError",
    "DrawingError",
    "DuplicateElementError",
    "DxfAuditError",
    "EffectiveDepthDivergedError",
    "EnginePreconditionError",
    "HookDoesNotFitError",
    "InputError",
    "LapTooLongError",
    "MalformedFileError",
    "MaterialError",
    "MaxLayersExceededError",
    "NoReinforcementLayoutError",
    "NoStirrupLayoutError",
    "NumericalError",
    "PillarInputError",
    "PillarTooSmallError",
    "ReinforcementAreaExceededError",
    "SheetFitError",
    "SkinReinforcementNoRoomError",
    "SkinSteelError",
    "SlabDesignError",
    "SlabInputError",
    "SlabLoweredTooMuchError",
    "SlabPreSizingDivergedError",
    "SlabThicknessExceededError",
    "SpliceDiameterError",
    "SplicePositionError",
    "SteelPriceNotFoundError",
    "StirrupBendUndefinedError",
    "StirrupSpacingTooSmallError",
    "StrutCrushingError",
    "SupportBarsShortError",
    "TableLookupError",
    "UnknownNameError",
    "UnknownPillarError",
]
