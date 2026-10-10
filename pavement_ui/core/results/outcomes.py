"""Possible outcomes of a pavement design and of an isolated beam design."""

from dataclasses import dataclass

from pavement_ui.core.results.beam_result import BeamResult
from pavement_ui.core.results.slab_result import SlabResult


@dataclass(frozen=True, slots=True)
class DesignSuccess:
    """The pavement was dimensioned"""

    beams: tuple[BeamResult, ...]
    slabs: tuple[SlabResult, ...]


@dataclass(frozen=True, slots=True)
class RuleFailure:
    """The engine refused the structure; message is the engine's original text"""

    message: str


@dataclass(frozen=True, slots=True)
class UnexpectedFailure:
    """An unexpected error in the calculation

    Attributes:
        message: Error text.
        details: Full traceback.
    """

    message: str
    details: str


@dataclass(frozen=True, slots=True)
class IsolatedBeamSuccess:
    """The isolated beam was dimensioned

    Attributes:
        self_weight_kn_m: Own-weight load used (kN/m).
    """

    result: BeamResult
    self_weight_kn_m: float


@dataclass(frozen=True, slots=True)
class IsolatedInvalidInput:
    """The engine refused the inputs (e.g. b < 12 cm); original engine text"""

    message: str


@dataclass(frozen=True, slots=True)
class IsolatedNotVerified:
    """The section could not be dimensioned; original engine text"""

    message: str


type DesignOutcome = DesignSuccess | RuleFailure | UnexpectedFailure
type IsolatedBeamOutcome = (
    IsolatedBeamSuccess | IsolatedInvalidInput | IsolatedNotVerified | UnexpectedFailure
)
