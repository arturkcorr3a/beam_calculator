# The Example 1 contains a more detailed analysis; this tests only the beam (single beam)

# input: width = 18 cm
# input: d = 85 cm
# input: height = 95 cm
# input: concrete = C20
# input: steel = CA50
# input: bending_moment = - 326,20 kN.m

# output: A_s = 14,97 cm

from src.calculators.rebar_calculator import RebarCalculator
from src.calculators.stirrup_calculator import StirrupCalculator
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.stirrups import Stirrups
from src.structural_elements.rectangular_beam import RectangularBeam


def create_v101_calculator() -> RebarCalculator:
    """Instantiate RebarCalculator for beam V101 from Carvalho Example 1

    Returns:
        Configured RebarCalculator with beam section properties and bending moment.

    References:
        Carvalho & Figueiredo Filho (2014) — Example 1
    """
    dummy_beam = RectangularBeam.__new__(RectangularBeam)
    dummy_beam.width = 18  # cm
    dummy_beam.height = 95  # cm
    dummy_beam._A = 18 * 95  # type: ignore # cm
    dummy_beam.concrete = Concrete.C20
    dummy_beam.steel = Steel.CA50
    dummy_beam.length = 800  # cm (arbitrary length for calculation purposes)

    dummy_stirrup_calculator = StirrupCalculator(dummy_beam, 0)
    dummy_stirrups = Stirrups(
        dummy_beam,
        dummy_stirrup_calculator,
    )

    return RebarCalculator(
        beam=dummy_beam,
        bending_moment=183.5,  # kN.m
        stirrups=dummy_stirrups,
        bending_moment_position=dummy_beam.length / 3,  # cm
        d=85,  # cm
        id="V101",
    )


def test_v101_effective_depth(calculator: RebarCalculator) -> None:
    """Verify that the preset effective depth (d) is preserved

    References:
        Carvalho & Figueiredo Filho (2014) — Example 1
    """
    assert calculator.d == 85


def test_v101_is_singly_reinforced(calculator: RebarCalculator) -> None:
    """Verify that beam V101 is singly reinforced

    References:
        Carvalho & Figueiredo Filho (2014) — Example 1
    """
    assert calculator.is_singly_reinforced is True


def test_v101_tensioned_rebar_area(calculator: RebarCalculator) -> None:
    """Verify required tension rebar area (As) matches Carvalho Example 1

    References:
        Carvalho & Figueiredo Filho (2014) — Example 1
    """
    expected_as = 7.64  # cm^2
    assert abs(calculator.tensioned_rebar_area - expected_as) < 0.02  # type: ignore[reportUnknownMemberType]


def main() -> None:
    """Run tests for beam V101 from Carvalho Example 1."""
    calculator = create_v101_calculator()
    calculator.calculate()
    test_v101_effective_depth(calculator)
    test_v101_is_singly_reinforced(calculator)
    test_v101_tensioned_rebar_area(calculator)
    print("All tests passed for beam V101.")


if __name__ == "__main__":
    main()
