from indeterminatebeam import UDLV, Support  # type: ignore

from src.calculators.rebar_calculator import RebarCalculator
from src.calculators.stirrup_calculator import StirrupCalculator
from src.config import APP_CONFIG
from src.loading.forces import design_effort_elu
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

    max_bending_moment, position = beam.get_max_bending_moment()  # kN.m
    max_shear_force = beam.get_shear_force(return_max=True)  # kN

    design_shear_force = design_effort_elu(max_shear_force)  # kN
    stirrup_calculator = StirrupCalculator(beam, design_shear_force)
    stirrups = Stirrups(beam, stirrup_calculator)

    calculator = RebarCalculator(beam, max_bending_moment, stirrups, position)
    calculator.calculate()


if __name__ == "__main__":
    main()
