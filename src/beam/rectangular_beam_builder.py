from .rectangular_beam import RectangularBeam
from indeterminatebeam.loading import Load
from indeterminatebeam import Support
from src.properties.concrete import Concrete

class RectangularBeamBuilder:
    """Builder class for creating rectangular beam instances."""
    
    def __init__(self):
        self._width = None
        self._height = None
        self._length = None
        self._concrete = Concrete.C40 # Default concrete strength at 40 MPa
        self._loads = []
        self._supports = []
        
    # CONFIRM na norma se existem constraints da relação da seção (por exemplo, para não ser viga-parede)
    def set_cross_section(self, width: float, height: float):
        """Set the width and height of the beam's cross-section (cm)."""
        self._width = width
        self._height = height
        return self
        
    # TODO conferir na norma se existem constraints
    def set_length(self, length: float):
        """Set the length of the beam (cm)."""
        self._length = length
        return self
        
    def set_concrete(self, concrete: Concrete):
        """Set the material properties of the beam (MPa)."""
        self._concrete = concrete
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
            concrete=self._concrete,
            loads=self._loads,
            supports=self._supports
        )