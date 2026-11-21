"""Tests for src/calculators/isolated_beam.py."""

import pytest

from src.calculators.isolated_beam import (
    CustomLoad,
    IsolatedPillar,
    OwnWeightLoad,
    WallLoad,
    build_isolated_beam,
    detail_isolated_beam,
)
from src.config import APP_CONFIG
from src.config_options import ExposureClass
from src.errors import DeformationLimitExceededError, ReinforcementAreaExceededError
from src.loading.linear_loads import LinearLoads
from src.loading.load_component import LoadComponent, LoadKind
from src.pavement_elements.continuous_beam import ContinuousBeam, WallDefinition
from src.pavement_elements.pillar import Pillar
from src.properties.concrete import Concrete
from tests.helpers import assert_approx

_PILLAR = IsolatedPillar(20.0, 20.0)
_WALL = WallDefinition(
    masonry_type="hollow concrete block",
    nominal_thickness=14,
    coating_thickness=1,
)
# 15 × 40 cm: g = 25 kN/m³ × 0.15 m × 0.40 m = 1.5 kN/m
_OWN_WEIGHT_KN_M = 1.5


def _two_spans(
    loads: list[OwnWeightLoad | WallLoad | CustomLoad],
) -> tuple[ContinuousBeam, dict[str, Pillar]]:
    """Build a 15 × 40 cm beam over spans of 4.00 m and 5.00 m."""
    return build_isolated_beam([400.0, 500.0], 15.0, 40.0, [_PILLAR] * 3, loads)


class TestGeometry:
    """Pillars are laid along x at the cumulative span lengths."""

    def test_pillar_ids_and_positions(self) -> None:
        _, pillars = _two_spans([])
        assert [(p.id, p.x, p.y) for p in pillars.values()] == [
            ("P1", 0.0, 0.0),
            ("P2", 400.0, 0.0),
            ("P3", 900.0, 0.0),
        ], "pillars should sit at the cumulative span lengths (cm)"

    def test_span_count(self) -> None:
        beam, _ = _two_spans([])
        assert len(beam.spans) == 2, "two lengths should give two spans"

    def test_effective_lengths_equal_axis_distances(self) -> None:
        beam, pillars = _two_spans([])
        for span, expected in zip(beam.spans, (400.0, 500.0), strict=True):
            assert_approx(
                span.get_effective_length(pillars),
                expected,
                "effective span should equal the axis distance (cm)",
            )

    def test_section_is_kept(self) -> None:
        beam, _ = _two_spans([])
        assert (beam.id, beam.width, beam.height) == ("V1", 15.0, 40.0), (
            "the given id and section should be kept, without pre-sizing"
        )


class TestLoads:
    """Each load is added to the spans it names."""

    def test_own_weight_on_every_span(self) -> None:
        beam, _ = _two_spans([OwnWeightLoad()])
        for span in beam.spans:
            assert_approx(
                span.permanent_load,
                _OWN_WEIGHT_KN_M,
                "own weight should be 25·b·h on every span (kN/m)",
            )

    def test_load_on_one_span(self) -> None:
        beam, _ = _two_spans([CustomLoad("revestimento", 3.0, span_index=1)])
        assert beam.spans[0].permanent_load == 0.0, "span 1 should stay unloaded"
        assert beam.spans[1].load_components == [
            LoadComponent(LoadKind.CUSTOM, "revestimento", 3.0)
        ], "span 2 should get the custom permanent load with its label"

    def test_variable_load_sets_psi_2(self) -> None:
        beam, _ = _two_spans([CustomLoad("uso", 2.0, variable=True, psi_2=0.4)])
        span = beam.spans[0]
        assert (span.permanent_load, span.variable_load) == (0.0, 2.0), (
            "a variable load should add to q only (kN/m)"
        )
        assert span.psi_2 == 0.4, "the span should keep the load's psi_2"

    def test_wall_load(self) -> None:
        beam, _ = _two_spans([WallLoad(_WALL, 2.8, span_index=0)])
        expected = LinearLoads.get_wall_load(*_WALL.get_parameters_for_load(), 2.8)
        assert_approx(
            beam.spans[0].permanent_load,
            expected,
            "wall load should follow NBR 6120 Table 2 times the height (kN/m)",
        )
        assert beam.spans[1].permanent_load == 0.0, "span 2 should have no wall"


class TestInvalidInput:
    """Inconsistent inputs are refused with a ValueError."""

    def test_wrong_pillar_count(self) -> None:
        with pytest.raises(ValueError, match="needs 3 pillars"):
            build_isolated_beam([400.0, 500.0], 15.0, 40.0, [_PILLAR] * 2, [])

    def test_non_positive_length(self) -> None:
        with pytest.raises(ValueError, match="must be positive"):
            build_isolated_beam([0.0], 15.0, 40.0, [_PILLAR] * 2, [])

    def test_span_index_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="Load on span 3"):
            _two_spans([OwnWeightLoad(span_index=2)])

    def test_psi_2_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="psi_2"):
            _two_spans([CustomLoad("uso", 2.0, variable=True, psi_2=1.5)])

    def test_narrow_beam(self) -> None:
        with pytest.raises(ValueError, match="at least 12"):
            build_isolated_beam([400.0], 10.0, 40.0, [_PILLAR] * 2, [])

    def test_small_pillar(self) -> None:
        with pytest.raises(ValueError, match="at least 14"):
            build_isolated_beam([400.0], 12.0, 40.0, [IsolatedPillar(12, 30)] * 2, [])

    def test_pillar_not_covering_the_beam(self) -> None:
        with pytest.raises(ValueError, match="does not fully cover"):
            build_isolated_beam([400.0], 25.0, 40.0, [_PILLAR] * 2, [])


class TestDimensioning:
    """The built beam goes through the pavement beam pipeline."""

    @pytest.fixture
    def beam(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> tuple[ContinuousBeam, dict[str, Pillar]]:
        monkeypatch.setattr(APP_CONFIG, "exposure_class", ExposureClass.MODERATE)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)
        beam, pillars = _two_spans(
            [OwnWeightLoad(), CustomLoad("uso", 3.0, variable=True, psi_2=0.3)]
        )
        beam.dimension(pillars)
        detail_isolated_beam(beam)
        return beam, pillars

    def test_is_detailed(self, beam: tuple[ContinuousBeam, dict[str, Pillar]]) -> None:
        assert beam[0].detailing is not None, "the beam should be detailed"
        assert beam[0].detailing.bars, "the detailing should have bar runs"

    def test_bars_are_marked(
        self, beam: tuple[ContinuousBeam, dict[str, Pillar]]
    ) -> None:
        detailing = beam[0].detailing
        assert detailing is not None, "the beam should be detailed"
        assert all(bar.mark is not None for bar in detailing.bars), (
            "every bar run should get a mark"
        )
        assert detailing.bars_on_face(True)[0].mark == "N1", (
            "marks should start at N1 on the bottom face"
        )

    def test_hogging_at_the_interior_pillar(
        self, beam: tuple[ContinuousBeam, dict[str, Pillar]]
    ) -> None:
        analysis = beam[0].analysis
        assert analysis is not None, "the analysis should be kept"
        assert analysis.bending_moment(400.0) < 0, (
            "a continuous beam should hog over its interior pillar"
        )

    def test_reactions_balance_the_load(
        self, beam: tuple[ContinuousBeam, dict[str, Pillar]]
    ) -> None:
        analysis = beam[0].analysis
        assert analysis is not None, "the analysis should be kept"
        total = sum(analysis.reaction(x) for x in (0.0, 400.0, 900.0))  # kN
        assert_approx(
            total,
            (_OWN_WEIGHT_KN_M + 3.0) * 9.0,
            "reactions should add up to (g + q) × total length (kN)",
            abs_tol=1e-3,
        )


class TestDesignFailures:
    """Design failures leave dimension() with their type and the beam's id."""

    @pytest.fixture(autouse=True)
    def _materials(self, monkeypatch: pytest.MonkeyPatch) -> None:  # pyright: ignore[reportUnusedFunction]
        monkeypatch.setattr(APP_CONFIG, "exposure_class", ExposureClass.MODERATE)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)

    def test_deflection_over_the_limit(self) -> None:
        """15 × 30 cm over 8.00 m with g = 5 and q = 5 kN/m fails ELS-DEF"""
        beam, pillars = build_isolated_beam(
            [800.0],
            15.0,
            30.0,
            [_PILLAR] * 2,
            [
                OwnWeightLoad(),
                CustomLoad("g", 5.0),
                CustomLoad("uso", 5.0, variable=True, psi_2=0.3),
            ],
        )
        with pytest.raises(DeformationLimitExceededError) as raised:
            beam.dimension(pillars)
        error = raised.value
        assert error.beam_id == beam.id, "the error should name the beam"
        assert error.long_term_deflection > error.acceptable_deflection, (
            "the long-term deflection should exceed the limit"
        )
        assert str(error).startswith(f"Beam '{beam.id}': Deformation exceeds"), (
            "the text should keep the old prefixed message"
        )

    def test_reinforcement_over_the_maximum(self) -> None:
        """15 × 25 cm over 7.00 m with g = 8 and q = 4 kN/m needs more than 4% A_c"""
        beam, pillars = build_isolated_beam(
            [700.0],
            15.0,
            25.0,
            [_PILLAR] * 2,
            [
                OwnWeightLoad(),
                CustomLoad("g", 8.0),
                CustomLoad("uso", 4.0, variable=True, psi_2=0.3),
            ],
        )
        with pytest.raises(ReinforcementAreaExceededError) as raised:
            beam.dimension(pillars)
        assert raised.value.beam_id == beam.id, "the error should name the beam"
        assert_approx(raised.value.max_area, 15.0, "max area = 4% of 15 × 25 cm (cm²)")


class TestStaggering:
    """The span's bottom bars are staggered by layer (NBR 6118 - 18.3.2.3.1)."""

    @pytest.fixture
    def span_bars(self, monkeypatch: pytest.MonkeyPatch) -> list[tuple[float, float]]:
        """Dimension a 15 × 60 cm beam over one 5.00 m span with 30 kN/m

        Returns:
            The (left, right) bar lengths (cm) of each layer of the span's
            bottom bars, from the bottom face up.
        """
        monkeypatch.setattr(APP_CONFIG, "exposure_class", ExposureClass.MODERATE)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)
        beam, pillars = build_isolated_beam(
            [500.0], 15.0, 60.0, [_PILLAR] * 2, [OwnWeightLoad(), CustomLoad("x", 30.0)]
        )
        beam.dimension(pillars)
        span = next(
            r
            for r in beam.reinforcement
            if r.is_tensioned and r.is_bottom_reinforcement
        )
        return [
            (
                max(bar.left_length for bar in layer.bars),
                max(bar.right_length for bar in layer.bars),
            )
            for layer in span.chosen_bars
            if layer.bars
        ]

    def test_bars_take_two_layers(self, span_bars: list[tuple[float, float]]) -> None:
        assert len(span_bars) >= 2, "the example should need two layers"

    def test_innermost_layer_is_cut_first(
        self, span_bars: list[tuple[float, float]]
    ) -> None:
        first, innermost = span_bars[0], span_bars[-1]
        assert innermost[0] < first[0], "innermost layer shorter on the left"
        assert innermost[1] < first[1], "innermost layer shorter on the right"

    def test_layers_never_grow_inwards(
        self, span_bars: list[tuple[float, float]]
    ) -> None:
        for lower, upper in zip(span_bars, span_bars[1:], strict=False):
            assert upper[0] <= lower[0], "no layer longer than the one below (left)"
            assert upper[1] <= lower[1], "no layer longer than the one below (right)"
