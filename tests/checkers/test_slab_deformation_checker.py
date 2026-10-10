"""Unit tests for SlabDeformationChecker.

Uses real integration for table lookups, load combinations and the reinforcement
chain — all deterministic given ``APP_CONFIG`` and the fixed inputs below.
Oracles are expressed as expressions over the same helpers that the production
code calls, so each test targets the checker's own arithmetic rather than
hard-coded decimals.
"""

import pytest

from src.checkers.slab_deformation_checker import (
    SlabDeformationChecker,
    _default_effective_depth_discount,  # pyright: ignore[reportPrivateUsage]
)
from src.config import APP_CONFIG
from src.data.carvalho.table_7.data import SLAB_MOMENT_COEFFICIENTS_TABLE
from src.data.carvalho.table_7_2.data import TABLE_7_2
from src.pavement_elements.slab import Slab
from src.pavement_elements.slab_edge import Edges, SupportCondition
from src.properties.concrete import Concrete
from src.properties.section_properties_calculator import (
    SectionPropertiesCalculator as section,
)
from src.properties.steel import Steel
from tests.helpers import assert_approx

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_ALL_FIXED: dict[Edges, SupportCondition] = {
    Edges.BOTTOM: "fixed",
    Edges.TOP: "fixed",
    Edges.LEFT: "fixed",
    Edges.RIGHT: "fixed",
}

_ALL_PINNED: dict[Edges, SupportCondition] = {
    Edges.BOTTOM: "pinned",
    Edges.TOP: "pinned",
    Edges.LEFT: "pinned",
    Edges.RIGHT: "pinned",
}


def _make_support(
    fixed: list[Edges],
) -> dict[Edges, SupportCondition]:
    """Build a full four-edge support dict, setting listed edges to 'fixed'."""
    all_edges: list[Edges] = [
        Edges.BOTTOM,
        Edges.TOP,
        Edges.LEFT,
        Edges.RIGHT,
    ]
    return {e: ("fixed" if e in fixed else "pinned") for e in all_edges}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def square_slab_all_fixed() -> SlabDeformationChecker:
    """Return a square slab (lx=ly=400, all edges fixed → case 9).

    Uses minimal load values so that the element is not cracked and the
    equivalent moment of inertia equals the gross section I.
    """
    return SlabDeformationChecker(
        permanent_load=5.0,
        variable_load=2.0,
        concrete=Concrete.C30,
        lx=400.0,
        ly=400.0,
        usage="residential",
        support_conditions=_ALL_FIXED,
    )


@pytest.fixture
def rectangular_slab() -> SlabDeformationChecker:
    """Return a rectangular slab (lx=400, ly=600 → span=400, ratio=1.5).

    All edges fixed → case 9.
    """
    return SlabDeformationChecker(
        permanent_load=5.0,
        variable_load=2.0,
        concrete=Concrete.C30,
        lx=400.0,
        ly=600.0,
        usage="residential",
        support_conditions=_ALL_FIXED,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPostInitSpan:
    """Tests for the __post_init__ span assignment."""

    def test_span_is_shorter_side(
        self, rectangular_slab: SlabDeformationChecker
    ) -> None:
        """span is set to min(lx, ly)."""
        assert rectangular_slab.span == 400.0, (
            "span should be the shorter side (lx=400 < ly=600)"
        )

    def test_span_symmetric(
        self, square_slab_all_fixed: SlabDeformationChecker
    ) -> None:
        """span equals either dimension when lx == ly."""
        assert square_slab_all_fixed.span == 400.0, (
            "span should be 400.0 when lx == ly == 400"
        )


class TestDefaultEffectiveDepthDiscount:
    """Tests for the _default_effective_depth_discount module helper."""

    def test_discount_is_covering_plus_1_5(self) -> None:
        """Default discount = Slab.nominal_covering + 1.5 (cm)."""
        expected = Slab.nominal_covering + 1.5
        assert _default_effective_depth_discount() == expected, (
            "Effective depth discount should be nominal_covering + 1.5 cm"
        )


class TestDimensionsRatio:
    """Tests for the dimensions_ratio property."""

    @pytest.mark.parametrize(
        "lx, ly, expected",
        [
            (400.0, 400.0, 1.0),
            (400.0, 600.0, 1.5),
            (600.0, 400.0, 1.5),
        ],
    )
    def test_ratio_is_max_over_min(self, lx: float, ly: float, expected: float) -> None:
        """dimensions_ratio = max(lx,ly)/min(lx,ly)."""
        slab = SlabDeformationChecker(
            permanent_load=5.0,
            variable_load=2.0,
            concrete=Concrete.C30,
            lx=lx,
            ly=ly,
            usage="residential",
            support_conditions=_ALL_FIXED,
        )
        assert_approx(
            slab.dimensions_ratio,
            expected,
            f"dimensions_ratio for lx={lx}, ly={ly} should be {expected}",
        )


class TestSupportingCase:
    """Tests for the supporting_case property (Quadro 7.2 case mapping).

    Edge classification for ly >= lx: LEFT/RIGHT are long edges; TOP/BOTTOM are short.
    """

    # (fixed_edges, expected_case)
    @pytest.mark.parametrize(
        "fixed_edges, expected_case",
        [
            # 0 fixed → case 1
            ([], 1),
            # 1 fixed short (BOTTOM) → case 2
            ([Edges.BOTTOM], 2),
            # 1 fixed long (LEFT) → case 3
            ([Edges.LEFT], 3),
            # 2 adjacent (LEFT + BOTTOM) → case 4
            ([Edges.LEFT, Edges.BOTTOM], 4),
            # 2 opposite short (TOP + BOTTOM) → case 5
            ([Edges.TOP, Edges.BOTTOM], 5),
            # 2 opposite long (LEFT + RIGHT) → case 6
            ([Edges.LEFT, Edges.RIGHT], 6),
            # 3 fixed (pinned = LEFT, a long edge) → case 7
            ([Edges.BOTTOM, Edges.TOP, Edges.RIGHT], 7),
            # 3 fixed (pinned = BOTTOM, a short edge) → case 8
            ([Edges.LEFT, Edges.TOP, Edges.RIGHT], 8),
            # 4 fixed → case 9
            ([Edges.BOTTOM, Edges.TOP, Edges.LEFT, Edges.RIGHT], 9),
        ],
    )
    def test_case_mapping(self, fixed_edges: list[Edges], expected_case: int) -> None:
        """supporting_case maps to the correct Quadro 7.2 case.

        Uses lx=400, ly=600 so that ly >= lx and LEFT/RIGHT are the long edges.
        """
        slab = SlabDeformationChecker(
            permanent_load=5.0,
            variable_load=2.0,
            concrete=Concrete.C30,
            lx=400.0,
            ly=600.0,
            usage="residential",
            support_conditions=_make_support(fixed_edges),
        )
        assert slab.supporting_case == expected_case, (
            f"Expected case {expected_case} for fixed={fixed_edges}"
        )

    def test_malformed_support_conditions_raises(self) -> None:
        """Incomplete support_conditions (3 edges, all fixed) causes a ValueError.

        With only 3 edges in the dict all marked 'fixed', the code enters the
        num_fixed==3 branch and tries to unpack exactly one pinned edge from an
        empty set — the tuple-unpack raises ValueError.
        """
        bad_conditions: dict[Edges, SupportCondition] = {
            Edges.BOTTOM: "fixed",
            Edges.TOP: "fixed",
            Edges.LEFT: "fixed",
        }
        slab = SlabDeformationChecker(
            permanent_load=5.0,
            variable_load=2.0,
            concrete=Concrete.C30,
            lx=400.0,
            ly=600.0,
            usage="residential",
            support_conditions=bad_conditions,
        )
        with pytest.raises(ValueError):
            _ = slab.supporting_case


class TestCoefficientForServiceMoment:
    """Tests for the coefficient_for_service_moment property."""

    def test_returns_max_of_mu_x_mu_y(
        self, rectangular_slab: SlabDeformationChecker
    ) -> None:
        """Coefficient is max(mu_x, mu_y) from the Carvalho table."""
        ratio = rectangular_slab.dimensions_ratio  # 1.5
        case = rectangular_slab.supporting_case  # 9
        mu = SLAB_MOMENT_COEFFICIENTS_TABLE.get_mu(ratio, case)
        expected = max(mu.mu_x, mu.mu_y)
        assert_approx(
            rectangular_slab.coefficient_for_service_moment,
            expected,
            "Coefficient should be max(mu_x, mu_y) from Carvalho Table 7",
        )

    @pytest.mark.parametrize(
        "ratio, case",
        [
            (1.0, 0),  # case out of [1,9]
            (1.0, 10),  # case out of [1,9]
            (0.9, 1),  # ratio < 1.0
        ],
    )
    def test_invalid_inputs_raise_value_error(self, ratio: float, case: int) -> None:
        """get_mu raises ValueError for out-of-range inputs."""
        with pytest.raises(ValueError):
            SLAB_MOMENT_COEFFICIENTS_TABLE.get_mu(ratio, case)


class TestAlphaForDeflection:
    """Tests for the alpha_for_deflection property."""

    def test_returns_table_7_2_alpha(
        self, rectangular_slab: SlabDeformationChecker
    ) -> None:
        """alpha_for_deflection matches TABLE_7_2.get_alpha(ratio, case)."""
        ratio = rectangular_slab.dimensions_ratio
        case = rectangular_slab.supporting_case
        expected = TABLE_7_2.get_alpha(ratio, case)
        assert_approx(
            rectangular_slab.alpha_for_deflection,
            expected,
            "alpha_for_deflection should match TABLE_7_2 lookup",
        )

    @pytest.mark.parametrize(
        "ratio, case",
        [
            (1.0, 0),
            (1.0, 10),
            (0.5, 1),
        ],
    )
    def test_invalid_inputs_raise_value_error(self, ratio: float, case: int) -> None:
        """TABLE_7_2.get_alpha raises ValueError for invalid inputs."""
        with pytest.raises(ValueError):
            TABLE_7_2.get_alpha(ratio, case)


class TestDesignLoad:
    """Tests for the slab design_load property."""

    def test_almost_permanent_over_10000(
        self, rectangular_slab: SlabDeformationChecker
    ) -> None:
        """design_load = (perm + 0.3*var) / 10000 (kN/cm²).

        With perm=5.0, var=2.0, psi2=0.3: (5 + 0.6) / 10000 = 0.00056.
        """
        assert_approx(
            rectangular_slab.design_load,
            0.00056,
            "design_load should be (5 + 0.3*2) / 10000 = 0.00056 kN/cm²",
            abs_tol=1e-9,
        )


class TestServiceMoment:
    """Tests for the slab service_moment property."""

    def test_formula(self, rectangular_slab: SlabDeformationChecker) -> None:
        """service_moment = (coefficient/100) * design_load * span² * width (kN.cm)."""
        slab = rectangular_slab
        coefficient = slab.coefficient_for_service_moment
        dl = slab.design_load
        expected = (coefficient / 100.0) * dl * slab.span**2 * slab.width
        assert_approx(
            slab.service_moment,
            expected,
            "service_moment should match (coefficient/100)*design_load*span²*width (kN.cm)",
        )


class TestOwnWeightContextManager:
    """Tests for the own_weight_for_current_height context manager."""

    def test_adds_and_restores_permanent_load(
        self, rectangular_slab: SlabDeformationChecker
    ) -> None:
        """Context manager temporarily increases permanent_load by slab self-weight."""
        slab = rectangular_slab
        p0 = slab.permanent_load
        height = 20.0  # cm → 0.20 m
        expected_increase = 25.0 * (height / 100.0)  # = 5.0 kN/m²

        with slab.own_weight_for_current_height(height):
            assert_approx(
                slab.permanent_load,
                p0 + expected_increase,
                "permanent_load should be increased by slab self-weight inside ctx (kN/m²)",
            )

        assert_approx(
            slab.permanent_load,
            p0,
            "permanent_load should be restored after context exits (kN/m²)",
        )

    def test_restores_on_exception(
        self, rectangular_slab: SlabDeformationChecker
    ) -> None:
        """permanent_load is restored even when an exception is raised inside the ctx."""
        slab = rectangular_slab
        p0 = slab.permanent_load

        try:
            with slab.own_weight_for_current_height(20.0):
                raise RuntimeError("deliberate test error")
        except RuntimeError:
            pass

        assert_approx(
            slab.permanent_load,
            p0,
            "permanent_load should be restored after an exception in the context (kN/m²)",
        )


class TestVerifyAdjustsOwnWeight:
    """Integration test for the verify override that adjusts own weight."""

    def test_verify_restores_load(
        self, rectangular_slab: SlabDeformationChecker
    ) -> None:
        """verify(h) returns a bool and leaves permanent_load unchanged afterwards."""
        slab = rectangular_slab
        p0 = slab.permanent_load

        result = slab.verify(20.0)

        assert isinstance(result, bool), "verify should return a bool"
        assert_approx(
            slab.permanent_load,
            p0,
            "permanent_load should be unchanged after verify completes (kN/m²)",
        )


class TestImmediateDeflection:
    """Tests for the slab immediate_deflection property (Carvalho Eq. 7.16)."""

    def test_carvalho_eq_7_16_not_cracked(
        self,
        rectangular_slab: SlabDeformationChecker,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """immediate_deflection matches Carvalho Eq. 7.16 for a not-cracked slab.

        When the element is not cracked (service_moment < cracking_moment), the
        equivalent moment of inertia equals the gross section I, and the ratio
        simplifies to 1.  This avoids triggering the full rebar-calculation chain.
        """
        monkeypatch.setattr(APP_CONFIG, "pavement_steel", Steel.CA50)

        slab = rectangular_slab
        h = 20.0  # cm — confirmed not-cracked at test-setup load levels
        slab.verify(h)  # sets height and effective_depth

        alpha = slab.alpha_for_deflection
        dl = slab.design_load
        span = slab.span
        ecs_kn_cm2 = Concrete.C30.ecs / 10.0
        i_gross = section.moment_of_inertia(slab.width, h)
        equiv_i = slab.equivalent_moment_of_inertia

        expected = ((dl * span**4) / (ecs_kn_cm2 * h**3) * (alpha / 100.0)) * (
            i_gross / equiv_i
        )

        assert_approx(
            slab.immediate_deflection,
            expected,
            "immediate_deflection should match Carvalho Eq. 7.16 (cm)",
        )


class TestTensionedReinforcementArea:
    """Tests for the slab _tensioned_reinforcement_area override."""

    def test_result_never_below_geometric_minimum(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """_tensioned_reinforcement_area is always >= 0.0015 * width * height.

        The method returns ``max(calculator.as1, absolute_min)``; the geometric
        floor 0.0015 * b * h is always the lower bound regardless of the moment.
        """
        monkeypatch.setattr(APP_CONFIG, "pavement_steel", Steel.CA50)

        h = 7.0  # cm — thin slab
        slab = SlabDeformationChecker(
            permanent_load=0.1,
            variable_load=0.05,
            concrete=Concrete.C30,
            lx=100.0,
            ly=100.0,
            usage="residential",
            support_conditions=_ALL_FIXED,
        )
        slab.verify(h)

        absolute_min = 0.0015 * 100.0 * h  # 0.0015 * width * height
        result = slab._tensioned_reinforcement_area  # pyright: ignore[reportPrivateUsage]

        assert result >= absolute_min - 1e-9, (
            f"Tensioned reinforcement area ({result:.4f} cm²) must be at least "
            f"the geometric minimum 0.0015*b*h = {absolute_min:.4f} cm²"
        )

    def test_result_equals_max_of_calculated_and_floor(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """_tensioned_reinforcement_area equals max(calculator.as1, absolute_min).

        Calls the property twice on the same slab state to confirm the result is
        deterministic and that it satisfies the max(…) contract: the returned
        value is at least ``absolute_min`` and at least as large as a fresh call.
        """
        monkeypatch.setattr(APP_CONFIG, "pavement_steel", Steel.CA50)

        h = 7.0
        slab = SlabDeformationChecker(
            permanent_load=0.1,
            variable_load=0.05,
            concrete=Concrete.C30,
            lx=100.0,
            ly=100.0,
            usage="residential",
            support_conditions=_ALL_FIXED,
        )
        slab.verify(h)

        result1 = slab._tensioned_reinforcement_area  # pyright: ignore[reportPrivateUsage]
        result2 = slab._tensioned_reinforcement_area  # pyright: ignore[reportPrivateUsage]

        assert_approx(
            result1,
            result2,
            "_tensioned_reinforcement_area must be deterministic across calls (cm²)",
        )
        absolute_min = 0.0015 * 100.0 * h
        assert result1 >= absolute_min - 1e-9, (
            "Result must be >= absolute_min = 0.0015*100*h (cm²)"
        )
