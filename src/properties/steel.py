from enum import Enum, EnumMeta
from functools import cached_property

from src.logger import log_property, logger_label

GAMMA_S = 1.15  # ABNT NBR 6118 - Section 12.4.1


class _SteelMeta(EnumMeta):
    @property
    def elastic_modulus(cls) -> int:
        """
        Returns the elastic modulus of steel (E_s) in kN/cm², based on ABNT NBR 6118 - Section 8.3.5.
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

    @property
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

    @property
    def fywd(self) -> float:
        """
        The design strength of steel (fywd) in kN/cm², based on ABNT NBR 6118 - Section 17.4.2.2
        """
        fyd = self.fyd
        result = min(fyd, 43.5)
        log_property(f"fywd = {result:.4f} kN/cm²")
        return result

    @property
    def fywk(self) -> float:
        """
        The characteristic strength of steel (fywk) in kN/cm², based on ABNT NBR 6118 - Section 17.4.1.1.1
        """
        result = min(self.value, 50)
        log_property(f"fywk = {result:.1f} kN/cm²")
        return result

    @property
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

    def is_size_available(self, diameter: float) -> bool:
        """
        Checks if a given rebar diameter (in mm) is available for the steel type.
        """
        return diameter in self.available_sizes
