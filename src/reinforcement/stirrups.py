from src.beam.rectangular_beam import RectangularBeam
from src.reinforcement.stirrup_calculator import MIN_SPACING, RectangularBeam

MIN_DIAMETER = 0.5  # cm, minimum diameter of stirrup bars (NBR 6118 - Section 18..3.3.2)

class Stirrups:
    """Class to manage stirrup reinforcement properties."""
    ''
    def __init__(self, beam: RectangularBeam):
        """
        Initialize Stirrups.
        """
        self.beam = beam
        self.spacing = None  # cm, to be calculated
        self.diameter = None  # cm, to be calculated
        self.steel = beam.steel  # Access steel properties from the beam
    
    def set_required_ratio(self, required_ratio: float) -> None:
        """
        Set the required stirrup reinforcement ratio (A_sw/s) in cm²/cm.
        """
        self.required_ratio = required_ratio

    @property
    def max_diameter(self) -> float:
        """
        Calculate the maximum diameter of stirrup bars (phi_max) in cm, based on the required reinforcement ratio and minimum spacing.
        """
        return self.beam.width / 10 # cm
    
    def choose(self) -> None:
        """
        Choose the diameter and spacing of stirrup bars based on the required reinforcement ratio, minimum spacing, and maximum diameter.
        """
        # IMPLEMENT setar espaçamento máximo e escolher a bitola que atenda
        # iterar diminuindo o espaçamento para encontrar o ratio mais próximo do necessário (otimização)
        pass