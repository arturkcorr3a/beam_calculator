from enum import Enum, EnumMeta
from functools import cached_property

from src.logger import log_property, logger_label

GAMMA_S = 1.15  # ABNT NBR 6118 - Section 12.4.1


class _SteelMeta(EnumMeta):
    @property
    def elastic_modulus(cls) -> int:
        """
        Returns the elastic modulus of steel (E_s) in MPa, based on ABNT NBR 6118 - Section 8.3.5.
        """
        return 210_000


@logger_label("{name}")
class Steel(Enum, metaclass=_SteelMeta):
    """
    Possible steel yield strengths (fy) in kN/cm², based on ABNT NBR 6118 - Section 8.3.1.
    """

    CA25 = 25
    CA50 = 50
    CA60 = 60

    @cached_property
    def fyd(self) -> float:
        """
        The design strength of steel (fyd) in kN/cm², based on ABNT NBR 6118 - Section 12.3.1
        """
        result = self.value / GAMMA_S
        log_property(f"fyd  = {result:.4f} kN/cm²")
        return result

    @cached_property
    def available_sizes(self) -> list[float]:
        """
        Returns a list of available rebar sizes (diameters in mm) for the given steel type, based on ABNT NBR 7480.
        """
        match self:
            case Steel.CA25:
                return [6.3, 8, 10, 12.5, 16, 20, 22, 25, 32, 40]
            case Steel.CA50:
                return [6.3, 8, 10, 12.5, 16, 20, 22, 25, 32, 40]
            case Steel.CA60:
                return [3.4, 3.8, 4.2, 4.6, 5.0, 5.5, 6.0, 6.4, 7.0, 8.0, 9.5, 10.0]
        return []

    @cached_property
    def fywd(self) -> float:
        """
        The design strength of steel (fywd) in kN/cm², based on ABNT NBR 6118 - Section 17.4.2.2
        """
        fyd = self.fyd
        result = min(fyd, 43.5)
        log_property(f"fywd = {result:.4f} kN/cm²")
        return result

    @cached_property
    def fywk(self) -> float:
        """
        The characteristic strength of steel (fywk) in kN/cm², based on ABNT NBR 6118 - Section 17.4.1.1.1
        """
        result = min(self.value, 50)
        log_property(f"fywk = {result:.1f} kN/cm²")
        return result

    @cached_property
    def bond_coefficient(self) -> float:
        """
        The bond coefficient (eta_1) for the steel type, based on ABNT NBR 6118 - Section 8.3.2 - Table 8.2
        """
        match self:
            case Steel.CA25:
                return 1.00
            case Steel.CA50:
                return 2.25
            case Steel.CA60:
                return 1.00
        return 1.0

    def bend_pin_diameter(self, diameter_mm: float) -> float:
        """Return the bending pin diameter (D) for a hook of the given bar

        Args:
            diameter_mm: Bar diameter φ (mm).

        Returns:
            Pin diameter in cm.

        Raises:
            ValueError: If the norm gives no pin for the bar (CA-60 with
                φ >= 20 mm).

        References:
            ABNT NBR 6118:2026 — Section 9.4.2.3, Table 9.1
        """
        is_small = diameter_mm < 20
        match self:
            case Steel.CA25:
                ratio = 4 if is_small else 5
            case Steel.CA50:
                ratio = 5 if is_small else 8
            case Steel.CA60:
                if not is_small:
                    raise ValueError(
                        f"No bending pin for CA-60 bars with {diameter_mm} mm (φ >= 20 mm)."
                    )
                ratio = 6
        return ratio * diameter_mm / 10

    def frame_joint_bend_diameter(self, diameter_mm: float) -> float:
        """Return the inner bend diameter (D) of a longitudinal bar bent in a frame joint

        Args:
            diameter_mm: Bar diameter φ (mm).

        Returns:
            Bend diameter in cm: 10φ for CA-25, 15φ for CA-50 and 18φ for CA-60.

        References:
            ABNT NBR 6118:2026 — Section 18.2.2
        """
        match self:
            case Steel.CA25:
                ratio = 10
            case Steel.CA50:
                ratio = 15
            case Steel.CA60:
                ratio = 18
        return ratio * diameter_mm / 10

    def stirrup_bend_diameter(self, diameter_mm: float) -> float:
        """Return the inner bend diameter (D) of a stirrup bar

        Args:
            diameter_mm: Stirrup bar diameter φ_t (mm).

        Returns:
            Bend diameter in cm.

        Raises:
            ValueError: If the norm gives no diameter for the bar (CA-60 with
                φ_t > 10 mm).

        References:
            ABNT NBR 6118:2026 — Section 9.4.6.1, Table 9.2
        """
        if diameter_mm <= 10:
            ratio = 3
        else:
            is_small = diameter_mm < 20
            match self:
                case Steel.CA25:
                    ratio = 4 if is_small else 5
                case Steel.CA50:
                    ratio = 5 if is_small else 8
                case Steel.CA60:
                    raise ValueError(
                        f"No stirrup bend diameter for CA-60 bars with {diameter_mm} mm (φ_t > 10 mm)."
                    )
        return ratio * diameter_mm / 10

    def is_size_available(self, diameter: float) -> bool:
        """
        Checks if a given rebar diameter (in mm) is available for the steel type.
        """
        return diameter in self.available_sizes
