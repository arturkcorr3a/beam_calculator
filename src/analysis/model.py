from dataclasses import dataclass


@dataclass(frozen=True)
class BeamSupport:
    """A beam support that always restrains horizontal and vertical translation.

    Attributes:
        position: Position along the beam axis (cm).
        rotational_stiffness: Rotational spring stiffness (kN.m/rad). ``0.0`` models a pinned support and ``math.inf`` a fully fixed one.
    """

    position: float
    rotational_stiffness: float = 0.0


@dataclass(frozen=True)
class DistributedLoad:
    """A uniform vertical load distributed over part of the beam.

    Attributes:
        start: Start position along the beam axis (cm).
        end: End position along the beam axis (cm).
        intensity: Load intensity (kN/m), positive downward.
    """

    start: float
    end: float
    intensity: float
