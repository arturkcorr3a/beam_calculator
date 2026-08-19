from src.properties.concrete import Concrete


class LinearLoads:
    @staticmethod
    def get_concrete_element_own_weight(area: float, reinforced: bool = True) -> float:
        """
        Calculate the own weight of a linear concrete element.

        Args:
            area (float): The area of the concrete element in square meters.
            reinforced (bool): Whether the concrete is reinforced or not.

        Returns:
            float: The own weight of the concrete element in kN/m².
        """
        concrete_density = Concrete.density(reinforced)

        own_weight = concrete_density * area
        return own_weight

    @staticmethod
    def get_wall_load():
        # TODO: Implement wall load calculation based on the wall's dimensions and material properties. 
        # Tabela 2 da ABN NBT 6120 - acho que vou ter que fazer um JSONzao ou um dataclass ou um dicionario pra conseguir navegar
        # Ver limitações e documentar!!!!!
        pass