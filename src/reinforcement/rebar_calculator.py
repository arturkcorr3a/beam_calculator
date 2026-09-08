from functools import cached_property
from math import sqrt

from src.elements.rectangular_beam import RectangularBeam
from src.loading.forces import (
    design_effort_elu,
    max_design_bending_moment,
    min_design_bending_moment,
)
from src.logger import log_element, log_iteration
from src.properties.steel import Steel
from src.reinforcement.reinforcement import Reinforcement
from src.reinforcement.stirrup_calculator import StirrupCalculator
from src.reinforcement.stirrups import Stirrups

# TODO find reference for this (just a first guess)
DEFAULT_STIRRUP_DIAMETER_FOR_D_CALCULATION = (
    1.0  # cm, default diameter of stirrup bars if not chosen (10 mm)
)


class RebarCalculator:
    """
    Class responsible for calculating the required rebar area for a rectangular beam.
    """

    def __init__(
        self, beam: RectangularBeam, bending_moment: float, stirrups: Stirrups
    ):
        """Initialize the RebarCalculator with a rectangular beam and its design bending moment.

        Args:
            beam: Rectangular beam section.
            bending_moment: Characteristic bending moment (kN.m).
            stirrups: Stirrups instance for the beam.
        """
        self.beam = beam
        bending_moment_in_kncm = bending_moment * 100
        self.design_bending_moment = design_effort_elu(bending_moment_in_kncm)
        self.tensioned_reinforcement = Reinforcement(self.beam)
        self.compressed_reinforcement = Reinforcement(self.beam)
        self.stirrups = stirrups

    def update_bending_moment(self, bending_moment: float) -> None:
        """Update the bending moment for rebar calculation.

        Args:
            bending_moment: Design bending moment (kN.m).
        """
        bending_moment_in_kncm = bending_moment * 100
        self.design_bending_moment = design_effort_elu(bending_moment_in_kncm)
        self.cleanup()

    def cleanup(self) -> None:
        """
        Clears all cached properties to reset the internal state.
        This is useful when updating beam or bending moment properties.
        """
        cached_properties = [
            "tensioned_rebar_area",
            "compressed_rebar_area",
            "as1",
            "max_y",
            "d",
            "d_compressed",
            "corrected_sigma_s2",
        ]
        for prop in cached_properties:
            if hasattr(self, prop):
                delattr(self, prop)

    def calculate(self) -> None:
        beam_label = f"b={self.beam.width:.0f} x h={self.beam.height:.0f} cm"
        current_d = 0.0
        iter_n = 0
        while abs(current_d - self.d) > 0.1:
            iter_n += 1
            current_d = self.d
            self.cleanup()
            self.calculate_and_set_required_tensioned_rebar_area()
            self.tensioned_reinforcement.set_required_area(self.tensioned_rebar_area)
            if not self.is_singly_reinforced:
                self.compressed_reinforcement.set_required_area(
                    self.compressed_rebar_area
                )
            self.stirrups.calculate_and_choose(self.d)
            as2 = 0.0 if self.is_singly_reinforced else self.compressed_rebar_area
            log_iteration(
                f"d={self.d:.2f} cm | As1={self.tensioned_rebar_area:.3f} cm2 | "
                f"As2={as2:.3f} cm2 | dd={abs(current_d - self.d):.3f} cm"
            )
        final_as2 = 0.0 if self.is_singly_reinforced else self.compressed_rebar_area
        log_element(
            f"d={self.d:.2f} cm | As1={self.tensioned_rebar_area:.3f} cm2 | As2={final_as2:.3f} cm2",
            label=beam_label,
        )

    def calculate_and_set_required_tensioned_rebar_area(self) -> None:
        """
        Calculate the required rebar area for a rectangular beam, ensuring it falls within the allowable limits.
        """
        self.tensioned_rebar_area = max(
            self.tensioned_rebar_area, self.min_tension_rebar_area
        )
        if (
            self.tensioned_rebar_area + self.compressed_rebar_area
        ) > self.max_rebar_area:
            raise ValueError("Required rebar area exceeds maximum allowable limit.")

    @property
    def min_tension_rebar_area(self) -> float:
        """
        Minimum tension rebar area (cm²), according to ABNT NBR 6118 - Section 17.3.5.2.1
        """
        md_min = min_design_bending_moment(self.beam)  # kN.cm

        stirrup_calculator = StirrupCalculator(self.beam, 0)
        stirrups = Stirrups(self.beam, stirrup_calculator)
        calculator = RebarCalculator(self.beam, 0, stirrups)

        calculator.design_bending_moment = md_min
        calculator.d = self.d  # cm
        calculated_min = calculator.as1  # cm^2
        absolute_min = 0.15 / 100 * self.beam.width * self.beam.height
        return max(calculated_min, absolute_min)

    @property
    def max_rebar_area(self) -> float:
        """
        Maximum rebar area (cm²) according to ABNT NBR 6118 - Section 17.3.5.2.4
        """
        return 0.04 * self.beam.area

    @property
    def is_singly_reinforced(self) -> bool:
        """
        Determines if the given rectangular beam can be classified as singly reinforced for the provided design bending moment.
        """
        return self.design_bending_moment <= max_design_bending_moment(
            self.beam, self.d, self.max_y
        )

    @cached_property
    def tensioned_rebar_area(self) -> float:
        """
        Calculates the required tensioned rebar area (cm²), As, for both single and double reinforcement cases.
        """
        return (
            self.as1
            if self.is_singly_reinforced
            else self.as1 + self.calculate_delta_as()
        )

    @cached_property
    def compressed_rebar_area(self) -> float:
        """
        Calculates the required compressed rebar area (cm²), As2, for double reinforcement cases, based on the difference between the design bending moment and the maximum bending moment that the beam can resist with single reinforcement, and the current rebar configuration.
        """
        delta_moment = self.calculate_delta_bending_moment()  # kN.cm
        return delta_moment / (self.corrected_sigma_s2 * (self.d - self.d_compressed))

    @cached_property
    def as1(self) -> float:
        """
        Calculates the required tensioned rebar area (As1) for the current design bending moment, based on the actual depth of the equivalent rectangular stress block (y) and equilibrium of internal forces.
        """
        uniform_stress = self.beam.concrete.calculate_uniform_stress()  # kN/cm²
        bw = self.beam.width  # cm
        y = self.actual_y if self.is_singly_reinforced else self.max_y  # cm
        return (uniform_stress * bw * y) / (self.beam.steel.fyd)

    def calculate_delta_as(self) -> float:
        """
        Calculates the additional tensioned rebar area (cm²) required when the beam is not singly reinforced, based on the stress in the compressed reinforcement and the current rebar configuration.
        """
        return (
            self.compressed_rebar_area * self.corrected_sigma_s2
        ) / self.beam.steel.fyd

    @cached_property
    def max_y(self) -> float:
        """
        Calculates the maximum depth (cm) of the equivalent rectangular stress block (y) to maintain both the deformation domain 3 and ductility.
        """
        return min(self.calculate_y_limit(), self.calculate_max_y_ductility())

    def calculate_y_limit(self) -> float:
        """
        Calculates the maximum depth (cm) of the equivalent rectangular stress block to maintain the deformation domain 3 (the limit is to turn to 4, as domain 2 would also be ok), based on ABNT NBR 6118 - Section 17.2.2.
        """
        lambda_c = self.beam.concrete.lambda_c  # no unit
        epsilon_cu = self.beam.concrete.epsilon_cu  # no unit
        steel_elastic_modulus_in_kn_cm2 = (
            Steel.elastic_modulus / 10
        )  # convert MPa to kN/cm²
        fyd = self.beam.steel.fyd  # kN/cm²
        d = self.d  # cm

        return (
            lambda_c
            * (
                (epsilon_cu * steel_elastic_modulus_in_kn_cm2)
                / (fyd + epsilon_cu * steel_elastic_modulus_in_kn_cm2)
            )
            * d
        )

    def calculate_max_y_ductility(self) -> float:
        """
        Maximum depth (cm) of the equivalent rectangular stress block (y) to maintain ductility, based on ABNT NBR 6118 - Section 14.6.4.3.
        """
        if self.beam.concrete.value <= 50:
            return 0.45 * self.beam.concrete.lambda_c * self.d
        return 0.35 * self.beam.concrete.lambda_c * self.d

    @cached_property
    def d(self) -> float:
        """
        Calculates the effective depth (cm) of the beam, considering the nominal covering and reinforcements.
        """
        covering = self.beam.nominal_covering  # cm
        if self.tensioned_reinforcement.is_chosen:
            all_bars = [b for layer in self.tensioned_reinforcement.chosen_bars for b in layer]
            if all_bars:
                covering = max(b.effective_covering(covering) for b in all_bars)
        stirrup_diameter = (
            self.stirrups.diameter
            if self.stirrups.diameter is not None
            else DEFAULT_STIRRUP_DIAMETER_FOR_D_CALCULATION
        )  # cm
        return (
            self.beam.height
            - covering
            - self.tensioned_reinforcement.get_distance_for_d_calculation()
            - stirrup_diameter
        )

    @property
    def max_bending_moment(self) -> float:
        """
        Calculates the maximum bending moment (kN.cm) that the beam can resist with single reinforcement, for the current rebar configuration (due to effective depth and maximum y)
        """
        uniform_stress = self.beam.concrete.calculate_uniform_stress()  # kN/cm²
        bw = self.beam.width  # cm
        y_max = self.max_y  # cm
        d = self.d  # cm
        return uniform_stress * bw * y_max * (d - y_max * 0.5)  # kN.cm

    @property
    def actual_y(self) -> float:
        """
        Calculates the actual depth of the equivalent rectangular stress block (y) (cm) for the current effective depth and design bending moment. Based on equilibrium of internal forces and moment.
        """
        d = self.d  # cm
        uniform_stress = self.beam.concrete.calculate_uniform_stress()  # kN/cm²
        bw = self.beam.width  # cm
        return d - sqrt(d**2 - (2 * self.design_bending_moment) / (uniform_stress * bw))

    def calculate_epsilon_s2(self) -> float:
        """
        Calculates the strain in the compressed reinforcement (no unit) for the current rebar configuration, based on the actual depth of the equivalent rectangular stress block (y), the distance from the extreme compression fiber to the centroid of the compressed rebar (d'), and the maximum depth of the equivalent rectangular stress block (y).
        """
        epsilon_cu = self.beam.concrete.epsilon_cu  # no unit
        lambda_c = self.beam.concrete.lambda_c  # no unit
        return epsilon_cu * (self.max_y - lambda_c * self.d_compressed) / self.max_y

    @cached_property
    def d_compressed(self) -> float:
        """
        Calculates the distance (cm) from the extreme compression fiber to the centroid of the compressed rebar (d'), considering the current rebar configuration.
        """
        covering = self.beam.nominal_covering  # cm
        if self.compressed_reinforcement.is_chosen:
            all_bars = [b for layer in self.compressed_reinforcement.chosen_bars for b in layer]
            if all_bars:
                covering = max(b.effective_covering(covering) for b in all_bars)
        stirrup_diameter = (
            self.stirrups.diameter
            if self.stirrups.diameter is not None
            else DEFAULT_STIRRUP_DIAMETER_FOR_D_CALCULATION
        )  # cm
        return (
            covering
            + stirrup_diameter
            + self.compressed_reinforcement.get_distance_for_d_calculation()
        )

    def calculate_sigma_s2(self) -> float:
        """
        Calculates the stress in the compressed reinforcement (kN/cm²) for the current rebar configuration, based on the calculated strain and the steel elastic modulus, ensuring it does not exceed the maximum stress allowed for the steel (fyd).
        """
        steel_elastic_modulus_in_kn_cm2 = (
            Steel.elastic_modulus / 10
        )  # convert MPa to kN/cm²
        calculated_sigma_s2 = (
            self.calculate_epsilon_s2() * steel_elastic_modulus_in_kn_cm2
        )  # kN/cm²
        max_sigma_s2 = self.beam.steel.fyd  # kN/cm²
        return min(calculated_sigma_s2, max_sigma_s2)

    @cached_property
    def corrected_sigma_s2(self) -> float:
        """
        Calculates the corrected stress in the compressed reinforcement (kN/cm²), accounting for the area occupied by the reinforcement in the concrete compression zone.

        This correction ensures that the compressed reinforcement properly accounts for the stress contribution without affecting the calculation of the additional tensioned reinforcement.
        """
        sigma_s2 = self.calculate_sigma_s2()  # kN/cm²
        return sigma_s2 - self.beam.concrete.calculate_uniform_stress()

    def calculate_delta_bending_moment(self) -> float:
        """
        Calculates the difference (kN.cm) between the design bending moment and the maximum bending moment that the beam can resist with single reinforcement, for the current rebar configuration. This difference is used to determine the required compressed reinforcement area when the beam is not singly reinforced.
        """
        return self.design_bending_moment - self.max_bending_moment
