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
        epsilon_cu = self.concrete.calculate_epsilon_cu()
        steel_elastic_modulus = self.steel.get_elastic_modulus()
        fyd = self.steel.calculate_fyd()
        # TODO d => calcular conforme cobrimentos, etc. fazer método de recalcular com o número de barras para fazer iterativamente
        return lambda_c * ( (epsilon_cu*steel_elastic_modulus) / (fyd + epsilon_cu*steel_elastic_modulus) ) * d