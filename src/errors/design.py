"""Errors for elements that cannot be designed"""

from src.errors.base import BeamCalculatorError, beam_prefixed


class DesignError(BeamCalculatorError, ValueError):
    """The element cannot be designed as it is; a larger section or a stronger concrete may solve it"""


class BeamDesignError(DesignError):
    """A beam cannot be designed as it is

    Attributes:
        beam_id: Id of the beam, usually set by ``ContinuousBeam`` after the
            calculators raise; shown as a prefix of the message.
    """

    def __init__(self, message: str, *, beam_id: str | None = None) -> None:
        super().__init__(message)
        self.beam_id = beam_id

    def __str__(self) -> str:
        return beam_prefixed(self.beam_id, self.message)


class SlabDesignError(DesignError):
    """A slab cannot be designed as it is

    Attributes:
        slab_id: Id of the slab; the message already names it.
    """

    def __init__(self, message: str, *, slab_id: str) -> None:
        super().__init__(message)
        self.slab_id = slab_id


class DeformationLimitExceededError(BeamDesignError):
    """The long-term deflection at a point exceeds its limit (ELS-DEF)

    A taller section is the usual fix.

    Attributes:
        position: Point checked, from the beam's start (cm).
        immediate_deflection: Immediate deflection at the point (cm).
        long_term_deflection: Deflection including creep (cm).
        acceptable_deflection: Limit for the deflection (cm).

    References:
        ABNT NBR 6118:2026 — Section 13.3, Table 13.3
    """

    def __init__(
        self,
        *,
        position: float,
        immediate_deflection: float,
        long_term_deflection: float,
        acceptable_deflection: float,
    ) -> None:
        super().__init__(
            f"Deformation exceeds acceptable limits at {position:.2f} cm. "
            f"Immediate deflection: {immediate_deflection:.2f} cm, "
            f"Long-term deflection: {long_term_deflection:.2f} cm, "
            f"Acceptable deflection: {acceptable_deflection:.2f} cm."
        )
        self.position = position
        self.immediate_deflection = immediate_deflection
        self.long_term_deflection = long_term_deflection
        self.acceptable_deflection = acceptable_deflection


class ReinforcementAreaExceededError(BeamDesignError):
    """The required longitudinal reinforcement exceeds the maximum area of the section

    Attributes:
        required_area: Tension plus compression reinforcement required (cm²).
        max_area: Maximum reinforcement area of the section (cm²).

    References:
        ABNT NBR 6118:2026 — Section 17.3.5.2.4
    """

    def __init__(self, *, required_area: float, max_area: float) -> None:
        super().__init__(
            f"Required rebar area ({required_area:.3f} cm²) exceeds maximum "
            f"allowable limit ({max_area:.3f} cm²)."
        )
        self.required_area = required_area
        self.max_area = max_area


class StrutCrushingError(BeamDesignError):
    """The design shear force exceeds the resistance of the compressed struts

    Attributes:
        design_shear_force: Design shear force V_Sd (kN).
        strut_resistance: Compressed strut resistance V_Rd2 (kN).

    References:
        ABNT NBR 6118:2026 — Section 17.4.2.2
    """

    def __init__(self, *, design_shear_force: float, strut_resistance: float) -> None:
        super().__init__(
            f"Design shear force (V_Sd = {design_shear_force:.2f} kN) exceeds "
            f"compressed strut resistance (V_Rd2 = {strut_resistance:.2f} kN). "
            "Design not verified."
        )
        self.design_shear_force = design_shear_force
        self.strut_resistance = strut_resistance


class NoReinforcementLayoutError(BeamDesignError):
    """No bar combination fits in the section and anchors, even with clamps"""

    def __init__(self) -> None:
        super().__init__("No valid reinforcement combination found.")


class EffectiveDepthDivergedError(BeamDesignError):
    """The stirrups and the longitudinal bars of a span never agree on the effective depth

    Attributes:
        max_iterations: Passes tried before giving up.
    """

    def __init__(self, *, max_iterations: int) -> None:
        super().__init__(
            f"Effective depth (d) did not converge within {max_iterations} "
            "stirrup-longitudinal reinforcement passes."
        )
        self.max_iterations = max_iterations


class SlabThicknessExceededError(SlabDesignError):
    """No slab thickness up to the maximum meets the deflection limit

    Attributes:
        max_thickness: Largest thickness tried (cm).

    References:
        ABNT NBR 6118:2026 — Sections 13.3 and 19.3.1
    """

    def __init__(self, *, slab_id: str, max_thickness: int) -> None:
        super().__init__(
            f"Slab '{slab_id}' cannot be stabilized; required thickness exceeds "
            f"{max_thickness} cm.",
            slab_id=slab_id,
        )
        self.max_thickness = max_thickness


class SlabPreSizingDivergedError(DesignError):
    """The slabs are still being resized after the maximum number of passes

    Attributes:
        passes: Passes run.
        slab_ids: Ids of the slabs still being resized.
    """

    def __init__(self, *, passes: int, slab_ids: list[str]) -> None:
        super().__init__(
            f"Slab pre-sizing did not converge after {passes} passes; "
            f"still resizing: {', '.join(slab_ids)}."
        )
        self.passes = passes
        self.slab_ids = slab_ids


class SkinReinforcementNoRoomError(BeamDesignError):
    """The bottom and top bars leave no room for the skin reinforcement on the web

    A taller section is the usual fix.

    Attributes:
        band_height: Height of the web between the bottom and top bars (cm);
            zero or negative when they overlap.
        bars_per_face: Bars per face that did not fit, or None when there is no
            band at all.

    References:
        ABNT NBR 6118:2026 — Section 17.3.5.2.3
    """

    def __init__(
        self, message: str, *, band_height: float, bars_per_face: int | None = None
    ) -> None:
        super().__init__(message)
        self.band_height = band_height
        self.bars_per_face = bars_per_face
