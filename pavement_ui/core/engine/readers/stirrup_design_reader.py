"""Read the shear design of a span's stirrups."""

from typing import cast

from pavement_ui.core.results.beam_design import StirrupDesign
from src.reinforcement.stirrups import Stirrups


def read_stirrup_design(stirrups: Stirrups) -> StirrupDesign:
    """Return the resistances and A_sw/s ratios the span's stirrups were chosen for"""
    calculator = stirrups.calculator
    diameter_cm = cast(float, stirrups.diameter)
    spacing_cm = cast(float, stirrups.spacing)
    return StirrupDesign(
        d_cm=calculator.effective_depth,
        vsd_kn=calculator.design_shear_force,
        vrd2_kn=calculator.compressed_strut_resistance,
        vc_kn=calculator.concrete_contribution,
        vsw_kn=calculator.required_contribution,
        required_ratio_cm2_cm=cast(float, stirrups.required_ratio),
        min_ratio_cm2_cm=calculator.minimum_ratio,
        provided_ratio_cm2_cm=Stirrups.calculate_ratio(diameter_cm, spacing_cm),
        max_spacing_cm=calculator.max_spacing,
    )
