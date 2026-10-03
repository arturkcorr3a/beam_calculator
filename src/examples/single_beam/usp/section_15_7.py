from src.analysis.model import BeamSupport, DistributedLoad
from src.analysis.solver import analyse_beam
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

    v2 = BeamSupport(0)
    v3 = BeamSupport(length)
    supports = [v2, v3]

    # Upward loads (negative intensity), as in the original example
    p = DistributedLoad(0, length, -50)
    q = DistributedLoad(0, length, -10)
    loads = [p, q]

    beam = RectangularBeam(
        concrete=concrete,
        steel=steel,
        width=width,
        height=height,
        length=length,
    )
    analysis = analyse_beam(beam, supports, loads)

    interest_points = analysis.moment_extremes_per_segment()
    position, max_bending_moment = max(
        interest_points, key=lambda point: abs(point[1])
    )  # kN.m
    max_shear_force = analysis.max_shear_force()  # kN

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
