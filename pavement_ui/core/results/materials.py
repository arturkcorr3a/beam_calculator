"""Read model of the design's materials."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MaterialsInfo:
    """Concrete and steel of the design, with their main strengths

    Attributes:
        concrete: Concrete class name, such as "C30".
        steel: Steel name, such as "CA50".
        fck_mpa: Characteristic compressive strength (MPa).
        fcd_mpa: Design compressive strength (MPa).
        fctm_mpa: Mean tensile strength (MPa).
        fctd_mpa: Design tensile strength (MPa).
        ecs_mpa: Secant elastic modulus (MPa).
        fyk_mpa: Characteristic yield strength (MPa).
        fyd_mpa: Design yield strength (MPa).
        fywd_mpa: Design yield strength of the stirrups (MPa).
        beam_cover_cm: Nominal cover of the beams (cm).
        slab_cover_cm: Nominal cover of the slabs (cm).

    References:
        ABNT NBR 6118:2026 — Sections 7.4, 8.2, 8.3 and 12.3
    """

    concrete: str
    steel: str
    fck_mpa: float
    fcd_mpa: float
    fctm_mpa: float
    fctd_mpa: float
    ecs_mpa: float
    fyk_mpa: float
    fyd_mpa: float
    fywd_mpa: float
    beam_cover_cm: float
    slab_cover_cm: float
