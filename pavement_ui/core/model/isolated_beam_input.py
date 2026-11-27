"""Inputs of the isolated beam calculator: spans on pillars and a load list."""

from dataclasses import dataclass

from pavement_ui.core.model.records import WallRecord


@dataclass(frozen=True, slots=True)
class IsolatedPillarInput:
    """A pillar under the beam

    Attributes:
        width_cm: Extent along the beam (cm); the engine requires ≥ 14.
        depth_cm: Extent across the beam (cm); must cover the beam width b.
        pinned: Simple support, without the pillar's rotational stiffness.
    """

    width_cm: float
    depth_cm: float
    pinned: bool = False


@dataclass(frozen=True, slots=True)
class OwnWeightLoad:
    """The beam's own weight, from b × h

    Attributes:
        span_index: Zero-based span; None for every span.
    """

    span_index: int | None = None


@dataclass(frozen=True, slots=True)
class WallLoad:
    """A masonry wall standing on the beam

    Attributes:
        height_m: Wall height (m), > 0.
        span_index: Zero-based span; None for every span.
    """

    wall: WallRecord
    height_m: float
    span_index: int | None = None


@dataclass(frozen=True, slots=True)
class CustomLoad:
    """A uniform load given by the user

    Attributes:
        label: Name shown in the report.
        value_kn_m: Intensity (kN/m), positive downward.
        variable: Whether it is variable (q); otherwise permanent (g).
        psi_2: Quasi-permanent factor ψ2 in [0, 1]; used only when variable.
        span_index: Zero-based span; None for every span.
    """

    label: str
    value_kn_m: float
    variable: bool = False
    psi_2: float = 0.3
    span_index: int | None = None


type IsolatedLoadInput = OwnWeightLoad | WallLoad | CustomLoad


@dataclass(frozen=True, slots=True)
class IsolatedBeamInput:
    """A continuous beam on pillars with its loads

    Attributes:
        width_cm: Section width b (cm); the engine requires ≥ 12.
        height_cm: Section height h (cm), > 0.
        span_lengths_m: Distance between consecutive pillar axes (m), left to right.
        pillars: One per support, left to right (one more than the spans).
        loads: Loads, in the order they are listed.
    """

    width_cm: float
    height_cm: float
    span_lengths_m: tuple[float, ...]
    pillars: tuple[IsolatedPillarInput, ...]
    loads: tuple[IsolatedLoadInput, ...]
