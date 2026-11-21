from collections.abc import Callable
from math import ceil
from typing import NamedTuple

from src.config import APP_CONFIG
from src.errors import ClampsDoNotFitError
from src.logger import log_operation, log_property, logger_label
from src.properties.section_properties_calculator import (
    SectionPropertiesCalculator as section,
)
from src.reinforcement.clamps import Clamps

CLAMP_AREA_TOLERANCE_RATIO = 0.05


class AnchorageClampCalculatorLabel(NamedTuple):
    beam_label: str
    is_left: bool

    def __str__(self) -> str:
        position = "Left" if self.is_left else "Right"
        return f"{position} extremity of {self.beam_label}"


@logger_label("Anchorage Clamp Calculator - {label}")
class AnchorageClampCalculator:
    def __init__(
        self,
        *,
        moment_shift: float,
        effective_depth: float,
        design_shear: float,
        label_info: AnchorageClampCalculatorLabel,
        available_length: float,
        necessary_length: float,
        design_bond_strength: float,
        stirrup_inner_width: float,
        clamps_fit: Callable[[float, int], bool],
        existing_clamps: Clamps | None = None,
    ) -> None:
        """Store the data needed to choose the clamps at one extremity

        Args:
            moment_shift: Moment shift a_l (cm).
            effective_depth: Effective depth d (cm).
            design_shear: Design shear force V_d at the support (kN).
            available_length: Anchorage length inside the support (cm).
            necessary_length: Anchorage length the bars would need (cm).
            design_bond_strength: Design bond strength f_bd (kN/cm²).
            stirrup_inner_width: Width between the stirrup's inner faces (cm).
            clamps_fit: Whether a given clamp diameter (mm) and quantity fit in
                the reinforced half of the section.
            existing_clamps: Clamps already set on this side by another layer,
                reused when their area is enough.
        """
        self.moment_shift = moment_shift
        self.effective_depth = effective_depth
        self.design_shear = design_shear
        self.label = label_info
        self.available_length = available_length
        self.necessary_length = necessary_length
        self.design_bond_strength = design_bond_strength
        self.stirrup_width = stirrup_inner_width
        self.clamps_fit = clamps_fit
        self.existing_clamps = existing_clamps

    def run(self) -> Clamps:
        """Choose the clamps for this extremity, reusing the side's existing ones when they are enough

        Raises:
            ClampsDoNotFitError: If no clamp arrangement fits in the section.
        """
        force_on_rebar = self._calculate_force_on_rebar()
        force_on_clamp = self._calculate_force_on_clamp(force_on_rebar)
        required_area = self._calculate_required_clamp_area(force_on_clamp)
        existing = self.existing_clamps
        if existing is not None and existing.area >= required_area:
            log_operation(
                f"Reusing {existing.quantity} {existing.diameter:.1f} clamps ({existing.area:.2f} cm^2)"
            )
            return existing

        diameter, quantity = self._choose_clamps(required_area)
        required_length = self._calculate_required_clamp_length(diameter)
        chosen_clamps = Clamps(
            diameter=diameter,
            quantity=quantity,
            length=required_length,
            width=self.stirrup_width,
        )
        log_operation(
            f"Chosen {quantity} {diameter:.1f} clamps with {required_length:.2f} cm"
        )
        return chosen_clamps

    def _calculate_force_on_rebar(self) -> float:
        """Calculate the tensile force to be anchored at the extremity (R_sd)

        Returns:
            Force in kN.
        """
        # PAPER
        force_on_rebar = (self.moment_shift / self.effective_depth) * self.design_shear
        log_property(f"Force on rebar (R_sd) = {force_on_rebar:.2f} kN")
        return force_on_rebar

    def _calculate_force_on_clamp(self, force_on_rebar: float) -> float:
        """Calculate the share of the rebar force that the clamps must carry (R_sc)

        Args:
            force_on_rebar: Tensile force to be anchored, R_sd, in kN.

        Returns:
            Force in kN.
        """
        # PAPER
        r_sc = force_on_rebar * (1 - (self.available_length / self.necessary_length))
        log_property(f"Force on clamp (R_sc) = {r_sc:.2f} kN")
        return r_sc

    def _calculate_required_clamp_area(self, force_on_clamp: float) -> float:
        """Calculate the required clamp steel area (A_sc)

        Args:
            force_on_clamp: Force the clamps must carry, R_sc, in kN.

        Returns:
            Area in cm².
        """
        # PAPER
        a_sc = force_on_clamp / APP_CONFIG.pavement_steel.fyd
        log_property(f"Required clamp area (A_sc) = {a_sc:.2f} cm^2")
        return a_sc

    def _choose_clamps(self, required_area: float) -> tuple[float, int]:
        """Choose the clamp diameter and quantity for the required area

        All clamps use one diameter. For each available diameter, the fewest clamps whose legs reach the required area are kept if they fit in the section. Options within a small band of the smallest fitting area are tied; among them, fewer clamps win, then the smaller diameter. The ranking is a design decision, not a normative rule.

        Args:
            required_area: Required clamp steel area A_sc (cm²).

        Returns:
            The clamp diameter (mm) and the number of clamps.

        Raises:
            ClampsDoNotFitError: If no clamp arrangement fits in the section.
        """
        candidates: list[tuple[float, int, float]] = []  # (area cm², quantity, φ mm)
        for diameter in APP_CONFIG.pavement_steel.available_sizes:
            leg_area = section.circular_cross_sectional_area(diameter / 10)  # cm²
            quantity = max(1, ceil(required_area / (2 * leg_area)))
            if not self.clamps_fit(diameter, quantity):
                continue
            candidates.append((2 * quantity * leg_area, quantity, diameter))

        if not candidates:
            error = ClampsDoNotFitError(required_area=required_area)
            log_operation(error.message)
            raise error

        threshold_area = min(area for area, _, _ in candidates) * (
            1 + CLAMP_AREA_TOLERANCE_RATIO
        )  # cm²
        _, quantity, diameter = min(
            (c for c in candidates if c[0] <= threshold_area),
            key=lambda c: (c[1], c[2]),
        )
        log_property(
            "Fitting clamp options: "
            + ", ".join(f"{n}x{d:g}mm ({a:.2f} cm^2)" for a, n, d in candidates)
        )
        return diameter, quantity

    def _calculate_required_clamp_length(self, clamp_diameter: float) -> float:
        """Calculate the total clamp length (l_c)

        Args:
            clamp_diameter: Clamp bar diameter φ in mm.

        Returns:
            Length in cm.
        """
        # PAPER
        clamp_diameter_cm = clamp_diameter / 10  # Convert mm to cm
        l_b1 = (clamp_diameter_cm / 4) * (
            APP_CONFIG.pavement_steel.fyd / self.design_bond_strength
        )
        total_length = l_b1 + self.available_length
        log_property(
            f"Required clamp length (l_c = l_b1 + l_available) = {total_length:.2f} cm"
        )
        return total_length
