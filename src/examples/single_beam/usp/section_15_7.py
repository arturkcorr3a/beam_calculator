from typing import cast

from indeterminatebeam import UDLV, Support  # type: ignore

from src.calculators.rebar_calculator import RebarCalculator
from src.calculators.stirrup_calculator import StirrupCalculator
from src.config import APP_CONFIG
from src.loading.forces import bending_moment_extremes_per_segment, design_effort_elu
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.stirrups import Stirrups  # type: ignore
from src.structural_elements.rectangular_beam import RectangularBeam


def main():
    width = 22  # cm
    height = 40  # cm
    concrete = Concrete.C25  # MPa
    steel = Steel.CA50
    length = 410  # cm

    APP_CONFIG.exposure_class = 1

    default_fixed = (1, 1, 0)
    v2 = Support(0, default_fixed)
    v3 = Support(length, default_fixed)
    supports = [v2, v3]

    default_span = (0, length)
    p = UDLV(50, default_span)
    q = UDLV(10, default_span)
    loads = [p, q]

    beam = RectangularBeam(
        concrete=concrete,
        steel=steel,
        width=width,
        height=height,
        length=length,
        loads=loads,
        supports=supports,
    )

    interest_points = bending_moment_extremes_per_segment(
        beam.bending_moment_expression, beam.shear_force_expression, 0.0, length
    )
    position, max_bending_moment = max(
        interest_points, key=lambda point: abs(point[1])
    )  # kN.m
    max_shear_force = cast(float, beam.get_shear_force(return_max=True))  # type: ignore # kN

    design_shear_force = design_effort_elu(max_shear_force)  # kN
    stirrup_calculator = StirrupCalculator(beam, design_shear_force)
    stirrups = Stirrups(beam, stirrup_calculator)

    calculator = RebarCalculator(
        beam=beam,
        bending_moment=max_bending_moment,
        stirrups=stirrups,
        bending_moment_position=position,
    )
    calculator.calculate()


if __name__ == "__main__":
    main()
