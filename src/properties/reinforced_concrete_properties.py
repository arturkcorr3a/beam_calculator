from src.properties.concrete import Concrete
from src.properties.steel import Steel

class ReinforcedConcretePropertiesCalculator:
    """
    Calculates properties specific to reinforced concrete sections, that depends both on concrete and steel properties.
    """
    def __init__(self, concrete: Concrete, steel: Steel):
        self.concrete = concrete
        self.steel = steel

    def calculate_y_limit(self) -> float:
        lambda_c = self.concrete.calculate_lambda_c()