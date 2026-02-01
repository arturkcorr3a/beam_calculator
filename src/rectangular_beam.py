from typing import Optional, List, Tuple
from indeterminatebeam import Beam, Support
from indeterminatebeam.loading import Load

class RectangularBeam(Beam):
    """
    Rectangular beam.
    """
    
    # FIXME
    def __init__(self, length: int, width: int, height: int, 
                 fck: int, supports: List[Support], loads: List[Load]):
        """
        Initialize a rectangular beam.
        
        Args:
            length: Beam length (m)
            width: Cross-section width (m)
            height: Cross-section height (m)
            elastic_modulus: Material elastic modulus (Pa)
            density: Material density (kg/m³)
        """
        super().__init__(length)
        # , supports=supports, loads=loads)
        self.length = length
        self.width = width
        self.height = height
        self.fck = fck
        self.beam: Optional[Beam] = None
        # TODO check how to receive properties in cm (change indeterminatebeam type or convert here)
        
    # TODO check
    @property
    def moment_of_inertia(self) -> float:
        """Calculate moment of inertia for rectangular section."""
        return (self.width * self.height ** 3) / 12
    
    @property
    def cross_sectional_area(self) -> float:
        """Calculate cross-sectional area."""
        return self.width * self.height
    
    # TODO
    def add_supports(self) -> None:
        """Add supports to the beam."""
        pass
    
    # TODO
    def add_loads(self) -> None:
        """Add loads to the beam."""
        pass
    
    # TODO
    def solve(self) -> None:
        """Solve the beam analysis."""
        pass
    
    # TODO
    def get_results(self) -> dict:
        """
        Get analysis results.
        
        Returns:
            Dictionary containing beam analysis results
        """
        pass