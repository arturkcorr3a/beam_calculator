from .rectangular_beam import RectangularBeam
from indeterminatebeam.loading import Load
from indeterminatebeam import Support
from properties.concrete_properties import Fck

class RectangularBeamBuilder:
    """Builder class for creating rectangular beam instances."""
    
    def __init__(self):
        self._width = None
        self._height = None
        self._length = None
        self._fck = 40 # Default concrete strength at 40 MPa
        self._loads = []
        self._supports = []
        
    # TODO conferir na norma se existem constraints
    def set_cross_section(self, width: float, height: float):
        """Set the width and height of the beam's cross-section (m)."""
        self._width = width
        self._height = height
        return self
        
    # TODO conferir na norma se existem constraints
    def set_length(self, length: float):
        """Set the length of the beam (m)."""
        self._length = length
        return self
        
    def set_fck(self, fck: Fck):
        """Set the material properties of the beam (MPa)."""
        self._fck = fck
        return self
    
    def add_load(self, load: Load):
        """Add a load to the beam."""
        self._loads.append(load)
        return self
    
    def set_load_case(self, load_case: list[Load]):
        """Set the load case for the beam."""
        self._loads = load_case
        return self
    
    def add_support(self, support: Support):
        """Add a support to the beam."""
        self._supports.append(support)
        return self
    
    def set_supports(self, supports: list[Support]):
        """Set the supports for the beam."""
        self._supports = supports
        return self
        
    def build(self):
        """Build and return the rectangular beam instance."""
        if self._width is None or self._height is None:
            raise ValueError("Width and height must be set")
        if self._length is None:
            raise ValueError("Length must be set")
        
        return RectangularBeam(
            width=self._width,
            height=self._height,
            length=self._length,
            fck=self._fck,
            loads=self._loads,
            supports=self._supports
        )