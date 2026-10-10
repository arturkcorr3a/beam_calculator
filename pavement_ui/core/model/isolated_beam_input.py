"""Inputs of the isolated (simply supported) beam calculator."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IsolatedBeamInput:
    """A simply supported beam loaded only by its own weight

    Attributes:
        length_m: Span (m), > 0.
        width_cm: Section width b (cm); the engine requires ≥ 12.
        height_cm: Section height h (cm), > 0.
        concrete_key: Concrete class key (e.g. "C30").
    """

    length_m: float
    width_cm: float
    height_cm: float
    concrete_key: str
