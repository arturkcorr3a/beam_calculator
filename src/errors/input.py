"""Errors for the data that describes the structure"""

from src.errors.base import BeamCalculatorError, beam_prefixed


class InputError(BeamCalculatorError, ValueError):
    """The data that describes the structure is refused by a rule"""


class BeamInputError(InputError):
    """The data of a beam is refused by a rule

    Attributes:
        beam_id: Id of the beam, or None where the rule does not know it (e.g. a
            bare section); the message already names the beam when it is known.
    """

    def __init__(self, message: str, *, beam_id: str | None = None) -> None:
        super().__init__(message)
        self.beam_id = beam_id


class SlabInputError(InputError):
    """The data of a slab is refused by a rule

    Attributes:
        slab_id: Id of the slab; the message already names it.
    """

    def __init__(self, message: str, *, slab_id: str) -> None:
        super().__init__(message)
        self.slab_id = slab_id


class PillarInputError(InputError):
    """The data of a pillar is refused by a rule

    Attributes:
        pillar_id: Id of the pillar.
    """

    def __init__(self, message: str, *, pillar_id: str) -> None:
        super().__init__(message)
        self.pillar_id = pillar_id


class BeamTooNarrowError(BeamInputError):
    """The beam is narrower than the minimum width

    Attributes:
        width: Beam width (cm).
        min_width: Minimum width (cm).

    References:
        ABNT NBR 6118:2026 — Section 13.2.2
    """

    def __init__(
        self, *, width: float, min_width: float, beam_id: str | None = None
    ) -> None:
        subject = "Beam width" if beam_id is None else f"Beam '{beam_id}' width"
        super().__init__(
            f"{subject} must be at least {min_width} cm. Got {width} cm.",
            beam_id=beam_id,
        )
        self.width = width
        self.min_width = min_width


class PillarTooSmallError(PillarInputError):
    """The pillar's cross-section is below the minimum dimension or area

    Attributes:
        width: Pillar width (cm).
        depth: Pillar depth (cm).

    References:
        ABNT NBR 6118:2026 — Section 13.2.3
    """

    def __init__(
        self, message: str, *, pillar_id: str, width: float, depth: float
    ) -> None:
        super().__init__(message, pillar_id=pillar_id)
        self.width = width
        self.depth = depth


class SlabLoweredTooMuchError(SlabInputError):
    """The slab is lowered more than its shortest supporting beam allows

    A taller beam or a smaller lowering is the fix.

    Attributes:
        lowered: Lowering of the slab (cm).
        max_lowered: Largest lowering allowed (cm).
        beam_id: Id of the shortest supporting beam.
        beam_height: Height of that beam (cm).
        thickness: Slab thickness (cm).
    """

    def __init__(
        self,
        *,
        slab_id: str,
        lowered: float,
        max_lowered: float,
        beam_id: str,
        beam_height: float,
        thickness: float,
    ) -> None:
        super().__init__(
            f"Slab '{slab_id}' is lowered {lowered} cm, but the maximum is "
            f"{max_lowered:.0f} cm (beam '{beam_id}' height {beam_height:.0f} cm "
            f"minus slab thickness {thickness} cm).",
            slab_id=slab_id,
        )
        self.lowered = lowered
        self.max_lowered = max_lowered
        self.beam_id = beam_id
        self.beam_height = beam_height
        self.thickness = thickness


class DuplicateElementError(InputError):
    """An element with the same id is already in the pavement

    Attributes:
        kind: Kind of element ("Pillar", "Beam" or "Slab").
        element_id: The repeated id.
    """

    def __init__(self, *, kind: str, element_id: str) -> None:
        super().__init__(f"{kind} '{element_id}' already exists.")
        self.kind = kind
        self.element_id = element_id


class UnknownPillarError(InputError):
    """An element refers to a pillar that is not in the pavement

    Attributes:
        owner_kind: Kind of the element that refers to it ("Beam" or "Slab").
        owner_id: Id of that element.
        pillar_id: The unknown pillar id.
    """

    def __init__(self, *, owner_kind: str, owner_id: str, pillar_id: str) -> None:
        super().__init__(
            f"{owner_kind} '{owner_id}': pillar '{pillar_id}' does not exist in the "
            "registry."
        )
        self.owner_kind = owner_kind
        self.owner_id = owner_id
        self.pillar_id = pillar_id


class MaterialError(InputError):
    """The project materials are refused by a rule"""


class ConcreteClassTooLowError(MaterialError):
    """The pavement concrete is below the minimum class for the exposure class

    Attributes:
        concrete: Name of the concrete (e.g. "C20").
        minimum_fck: Minimum characteristic strength (MPa).
        exposure_class: Environmental aggressiveness class (1 to 4).

    References:
        ABNT NBR 6118:2026 — Section 7.4.2, Table 7.1
    """

    def __init__(self, *, concrete: str, minimum_fck: int, exposure_class: int) -> None:
        super().__init__(
            f"Concrete {concrete} is below the minimum C{minimum_fck} required for "
            f"exposure class {exposure_class}."
        )
        self.concrete = concrete
        self.minimum_fck = minimum_fck
        self.exposure_class = exposure_class


class SkinSteelError(MaterialError):
    """A beam needs skin reinforcement, which the project steel cannot provide

    It is raised while the beam is dimensioned, so, like ``BeamDesignError``, it
    is named by ``ContinuousBeam`` and prefixed with the beam.

    Attributes:
        beam_height: Height of the beam (cm).
        min_height: Height above which skin reinforcement is required (cm).
        steel_grade: Yield strength grade of the project steel (e.g. 25 for CA-25).
        beam_id: Id of the beam, set by ``ContinuousBeam``; shown as a prefix of
            the message.

    References:
        ABNT NBR 6118:2026 — Section 17.3.5.2.3
    """

    def __init__(
        self,
        *,
        beam_height: float,
        min_height: float,
        steel_grade: int,
        beam_id: str | None = None,
    ) -> None:
        super().__init__(
            f"A beam with h = {beam_height:g} cm > {min_height:g} cm needs skin "
            "reinforcement in CA-50 or CA-60, but the project steel is "
            f"CA-{steel_grade}. Change the project steel to CA-50 or CA-60."
        )
        self.beam_height = beam_height
        self.min_height = min_height
        self.steel_grade = steel_grade
        self.beam_id = beam_id

    def __str__(self) -> str:
        return beam_prefixed(self.beam_id, self.message)
