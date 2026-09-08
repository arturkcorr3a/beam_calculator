from src.config import APP_CONFIG
from src.data.nbr6120_2019.table_4.data import TABLE_4
from src.data.nbr6120_2019.table_7.data import TABLE_7
from src.data.nbr6120_2019.table_8.data import TABLE_8
from src.data.nbr6120_2019.table_10.data import TABLE_10
from src.properties.concrete import Concrete


class SuperficialLoads:
    @staticmethod
    def get_concrete_element_own_weight(
        thickness: float, reinforced: bool = True
    ) -> float:
        """Calculate the own weight of a superficial concrete element (kN/m²).

        Based on concrete density from ABNT NBR 6120:2019, Table 1.

        Args:
            thickness: Thickness of the concrete element (m).
            reinforced: True for reinforced concrete, False for plain concrete.

        Returns:
            Own weight of the element (kN/m²).
        """
        concrete_density = Concrete.density(reinforced)

        own_weight = concrete_density * thickness
        return own_weight

    @staticmethod
    def get_infill_weight(material_description: str) -> float:
        """Calculate the weight of infill (kN/m²).

        Based on ABNT NBR 6120:2019, Table 7.

        Args:
            material_description: Description of the infill material.

        Returns:
            Weight of infill (kN/m²).
        """
        return TABLE_7.find_material(material_description).weight_avg

    @staticmethod
    def get_ceiling_weight(material_description: str) -> float:
        """Calculate the ceiling weight load (kN/m²).

        Based on ABNT NBR 6120:2019, Table 8.

        Args:
            material_description: Description of the ceiling material.

        Returns:
            Ceiling weight load (kN/m²).
        """
        return TABLE_8.find_material(material_description).weight

    @staticmethod
    def get_top_finish_weight(material_description: str, thickness: float) -> float:
        """Calculate the top finish weight load (kN/m²).

        Based on ABNT NBR 6120:2019, Table 4.

        Args:
            material_description: Description of the top finish material.
            thickness: Thickness of the top finish (cm).

        Returns:
            Top finish weight load (kN/m²).
        """
        return TABLE_4.find_material(material_description).get_weight(thickness)

    @staticmethod
    def get_variable_usage_load(local: str) -> float:
        """Calculate the variable usage load for a specific location (kN/m²).

        Based on ABNT NBR 6120:2019, Table 10.

        Args:
            local: Description of the location/usage category.

        Returns:
            Variable usage load (kN/m²).
        """
        building_category = APP_CONFIG.building_category

        return TABLE_10.find_category(building_category).get_location_load(local)
