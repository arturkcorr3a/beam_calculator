from enum import Enum
from typing import List
from functools import cached_property

GAMMA_S = 1.15  # ABNT NBR 6118 - Section 12.4.1

# TODO escolher um único aço para o dimensionamento: deixar o CA-50 como padrão e CA-25 e CA-60 como plano B (configuração adicional opcional) #CAO tipo aço
class Steel(Enum):
    """
    Possible steel yield strengths (fy) in kN/cm², based on ABNT NBR 6118 - Section 8.3.1.
    """
    CA25 = 25
    CA50 = 50
    CA60 = 60

    @property
    def elastic_modulus(self) -> int:
        """
        Returns the elastic modulus of steel (E_s) in MPa, based on ABNT NBR 6118 - Section 8.3.5.
        """
        return 210_000
    
    @property
    def fyd(self) -> float:
        """
        The design strength of steel (fyd) in kN/cm², based on ABNT NBR 6118 - Section 12.3.1 
        """
        return self.value / GAMMA_S
    
    @cached_property
    def available_sizes(self) -> List[float]:
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
        return min(self.fyd, 43.5)
    
    @property
    def fywk(self) -> float:
        """
        The characteristic strength of steel (fywk) in kN/cm², based on ABNT NBR 6118 - Section 17.4.1.1.1
        """
        return min(self.value, 50)
    
    def is_size_available(self, diameter: float) -> bool:
        """
        Checks if a given rebar diameter (in mm) is available for the steel type.
        """
        return diameter in self.available_sizes
    
    def get_area(self, diameter: float) -> float:
        """
        Returns the cross-sectional area (in cm²) of a rebar with the given diameter (in mm), based on ABNT NBR 7480.
        """
        bar_areas = {
            6.3: 31.2,
            8.0: 50.3,
            10.0: 78.5,
            12.5: 122.7,
            16.0: 201.1,
            20.0: 314.2,
            22.0: 380.1,
            25.0: 490.9,
            32.0: 804.2,
            40.0: 1256.6
        }
        wire_areas = {
            3.4: 9.1,
            3.8: 11.3,
            4.2: 13.9,
            4.6: 16.6,
            5.0: 19.6,
            5.5: 23.8,
            6.0: 28.3,
            6.4: 32.2,
            7.0: 38.5,
            8.0: 50.3,
            9.5: 70.9,
            10.0: 78.5
        }
        if not self.is_size_available(diameter):
            raise ValueError(f"Diameter {diameter} mm is not available for steel type {self.name}.")
        if self == Steel.CA25 or self == Steel.CA50:
            return bar_areas[diameter] / 100  # convert from mm² to cm²
        return wire_areas[diameter] / 100 # convert from mm² to cm²