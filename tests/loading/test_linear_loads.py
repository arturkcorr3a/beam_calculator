"""Unit tests for the linear (per-metre) load calculations."""

from src.loading.linear_loads import LinearLoads
from tests.helpers import assert_approx


class TestGetConcreteElementOwnWeight:
    """Tests for the own weight of a linear concrete element in kN/m."""

    def test_reinforced(self) -> None:
        expected_weight = 1.0  # kN/m (25.0 kN/m³ * 0.04 m²)
        assert (
            LinearLoads.get_concrete_element_own_weight(0.04, reinforced=True)
            == expected_weight
        ), "Reinforced 0.04 m² section should weigh 1.0 kN/m"

    def test_plain(self) -> None:
        expected_weight = 0.96  # kN/m (24.0 kN/m³ * 0.04 m²)
        assert_approx(
            LinearLoads.get_concrete_element_own_weight(0.04, reinforced=False),
            expected_weight,
            "Plain 0.04 m² section should weigh 0.96 kN/m",
        )

    def test_reinforced_small_area(self) -> None:
        expected_weight = 0.3  # kN/m (25.0 kN/m³ * 0.012 m²)
        assert_approx(
            LinearLoads.get_concrete_element_own_weight(0.012, reinforced=True),
            expected_weight,
            "Reinforced 0.012 m² section should weigh 0.3 kN/m",
        )


class TestGetWallLoad:
    """Tests for the distributed masonry wall load on a beam in kN/m."""

    def test_hollow_concrete_block_14cm_no_coating(self) -> None:
        # TABLE_2 HCB Class C, 14 cm, 0-coating -> 1.40 kN/m²
        expected_load = 4.2  # kN/m (1.40 * 3.0 m height)
        assert_approx(
            LinearLoads.get_wall_load(
                "Hollow concrete block (Class C - ABNT NBR 6136)", 14.0, 0, 3.0
            ),
            expected_load,
            "1.40 kN/m² wall over 3.0 m height should give 4.2 kN/m",
        )

    def test_hollow_concrete_block_14cm_one_cm_coating(self) -> None:
        # TABLE_2 HCB Class C, 14 cm, 1-coating -> 1.80 kN/m²
        expected_load = 5.4  # kN/m (1.80 * 3.0 m height)
        assert_approx(
            LinearLoads.get_wall_load(
                "Hollow concrete block (Class C - ABNT NBR 6136)", 14.0, 1, 3.0
            ),
            expected_load,
            "1.80 kN/m² wall over 3.0 m height should give 5.4 kN/m",
        )

    def test_wall_load_scales_with_height(self) -> None:
        # TABLE_2 HCB Class C, 14 cm, 0-coating -> 1.40 kN/m²
        expected_load = 1.4  # kN/m (1.40 * 1.0 m height)
        assert_approx(
            LinearLoads.get_wall_load(
                "Hollow concrete block (Class C - ABNT NBR 6136)", 14.0, 0, 1.0
            ),
            expected_load,
            "1.40 kN/m² wall over 1.0 m height should give 1.4 kN/m",
        )
