from typing import NamedTuple

from src.config import APP_CONFIG
from src.logger import log_operation, log_property, logger_label
from src.reinforcement.clamps import Clamps


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
        stirrup_width: float,
    ) -> None:
        self.moment_shift = moment_shift
        self.effective_depth = effective_depth
        self.design_shear = design_shear
        self.label = label_info
        self.available_length = available_length
        self.necessary_length = necessary_length
        self.design_bond_strength = design_bond_strength
        self.stirrup_width = stirrup_width

    def run(self) -> Clamps:
        force_on_rebar = self._calculate_force_on_rebar()
        force_on_clamp = self._calculate_force_on_clamp(force_on_rebar)
        required_area = self._calculate_required_clamp_area(force_on_clamp)
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
        # IMPLEMENT should return the clamp diameter and number of clamps needed based on the required area
        return (12.5, 1)  # Example values; replace with actual logic

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
