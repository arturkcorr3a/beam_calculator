"""Tests for src/pavement_elements/pavement.py."""

import types
from typing import cast

import pytest

import src.pavement_elements.pavement as pavement_module
from src.config import APP_CONFIG
from src.config_options import ExposureClass
from src.detailing.detailed_bar import DetailedBar
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.mark_registry import BarKey, MarkRegistry, bar_key
from src.pavement_elements.continuous_beam import ContinuousBeam, WallDefinition
from src.pavement_elements.geometry_utils import Alignment
from src.pavement_elements.pavement import Pavement, reset_element_id_counters
from src.pavement_elements.pillar import Pillar
from src.pavement_elements.slab import Slab
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.structural_elements.support import Support

# ---------------------------------------------------------------------------
# Helpers / doubles
# ---------------------------------------------------------------------------


def _make_detailing(beam_id: str, *bars: DetailedBar) -> DetailingBeam:
    """Build a 20 x 60 cm detailing beam with the given bars"""
    return DetailingBeam(
        beam_id=beam_id,
        width=20.0,
        height=60.0,
        nominal_covering=2.5,
        steel=Steel.CA50,
        supports=(Support(0.0, -10.0, 10.0), Support(500.0, 490.0, 510.0)),
        bars=list(bars),
    )


def _make_bar(end: float) -> DetailedBar:
    """Build a bottom run of 2 straight φ10 bars from 0 to the given end (cm)"""
    return DetailedBar(
        diameter_mm=10,
        steel=Steel.CA50,
        quantity=2,
        is_bottom=True,
        is_tensioned=True,
        layer_index=0,
        y=4.0,
        start=0,
        end=end,
    )


def _make_beam_double(
    beam_id: str = "V1", pillar_ids: tuple[str, str] = ("P1", "P2")
) -> ContinuousBeam:
    """Build a beam SimpleNamespace double recording calls to its methods."""
    calls: list[str] = []
    beam = types.SimpleNamespace(
        id=beam_id,
        pillar_ids=pillar_ids,
        calls=calls,
        detailing=None,
    )
    beam.clear_resolved = lambda: calls.append(f"clear_resolved:{beam_id}")
    beam.resolve_and_validate = lambda registry: calls.append(  # pyright: ignore[reportUnknownLambdaType]
        f"resolve_and_validate:{beam_id}"
    )
    beam.pre_size = lambda registry: calls.append(f"pre_size:{beam_id}")  # pyright: ignore[reportUnknownLambdaType]
    beam.load_spans = lambda: calls.append(f"load_spans:{beam_id}")
    beam.dimension = lambda registry: calls.append(f"dimension:{beam_id}")  # pyright: ignore[reportUnknownLambdaType]

    def detail() -> DetailingBeam:
        calls.append(f"detail:{beam_id}")
        return _make_detailing(beam_id)

    beam.detail = detail
    beam.report = lambda registry: f"report:{beam_id}"  # pyright: ignore[reportUnknownLambdaType]
    return cast(ContinuousBeam, beam)


def _make_slab_double(
    slab_id: str = "L1",
    pre_size_returns: list[bool] | None = None,
) -> Slab:
    """Build a slab SimpleNamespace double recording calls to its methods.

    Args:
        slab_id: The slab's id string.
        pre_size_returns: Sequence of values returned by successive pre_size(registry) calls.
            Defaults to [True] (stable on first call).
    """
    if pre_size_returns is None:
        pre_size_returns = [True]
    returns_iter = iter(pre_size_returns)
    calls: list[str] = []
    slab = types.SimpleNamespace(
        id=slab_id,
        corner_pillar_ids=("P1", "P2", "P3", "P4"),
        calls=calls,
    )
    slab.clear_resolved = lambda: calls.append(f"clear_resolved:{slab_id}")
    slab.resolve_and_validate = (
        lambda pillars, beams: calls.append(f"resolve_and_validate:{slab_id}")  # pyright: ignore[reportUnknownLambdaType]
    )
    slab.pre_size = lambda registry: next(returns_iter)  # pyright: ignore[reportUnknownLambdaType]
    slab.validate_lowered = lambda: calls.append(f"validate_lowered:{slab_id}")
    slab.unload_on_supporting_spans = lambda registry: calls.append(  # pyright: ignore[reportUnknownLambdaType]
        f"unload_on_supporting_spans:{slab_id}"
    )
    return cast(Slab, slab)


# ---------------------------------------------------------------------------
# TestAddPillar
# ---------------------------------------------------------------------------


class TestAddPillar:
    """add_pillar stores the pillar; duplicate raises."""

    def test_stores_pillar(self) -> None:
        p = Pavement()
        pillar = Pillar(x=0, y=0, width=20, depth=20)
        p.add_pillar(pillar)
        assert p.pillars[pillar.id] is pillar, "pillar should be stored by its id"

    def test_duplicate_raises(self) -> None:
        p = Pavement()
        pillar = Pillar(x=0, y=0, width=20, depth=20)
        p.add_pillar(pillar)
        with pytest.raises(ValueError, match="already exists"):
            p.add_pillar(pillar)


# ---------------------------------------------------------------------------
# TestAddBeam
# ---------------------------------------------------------------------------


class TestAddBeam:
    """add_beam stores the beam; duplicate raises."""

    def test_stores_beam(self) -> None:
        p = Pavement()
        beam = _make_beam_double("V_test")
        p.add_beam(beam)
        assert p.beams["V_test"] is beam, "beam should be stored by its id"

    def test_duplicate_raises(self) -> None:
        p = Pavement()
        beam = _make_beam_double("V_test")
        p.add_beam(beam)
        with pytest.raises(ValueError, match="already exists"):
            p.add_beam(beam)


# ---------------------------------------------------------------------------
# TestAddSlab
# ---------------------------------------------------------------------------


class TestAddSlab:
    """add_slab stores the slab; duplicate raises."""

    def test_stores_slab(self) -> None:
        p = Pavement()
        slab = _make_slab_double("L_test")
        p.add_slab(slab)
        assert p.slabs["L_test"] is slab, "slab should be stored by its id"

    def test_duplicate_raises(self) -> None:
        p = Pavement()
        slab = _make_slab_double("L_test")
        p.add_slab(slab)
        with pytest.raises(ValueError, match="already exists"):
            p.add_slab(slab)


# ---------------------------------------------------------------------------
# TestValidate
# ---------------------------------------------------------------------------


class TestValidate:
    """validate clears resolved state then calls resolve_and_validate on every element."""

    def test_concrete_below_exposure_minimum_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(APP_CONFIG, "exposure_class", ExposureClass.MODERATE)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C20)
        with pytest.raises(ValueError, match="below the minimum"):
            Pavement().validate()

    def test_calls_clear_then_resolve_on_all_beams(self) -> None:
        p = Pavement()
        beam1 = _make_beam_double("VA")
        beam2 = _make_beam_double("VB")
        p.add_beam(beam1)
        p.add_beam(beam2)

        p.validate()

        assert "clear_resolved:VA" in beam1.calls, (  # type: ignore[attr-defined]
            "clear_resolved should be called on beam VA"
        )
        assert "resolve_and_validate:VA" in beam1.calls, (  # type: ignore[attr-defined]
            "resolve_and_validate should be called on beam VA"
        )
        assert "clear_resolved:VB" in beam2.calls, (  # type: ignore[attr-defined]
            "clear_resolved should be called on beam VB"
        )
        assert "resolve_and_validate:VB" in beam2.calls, (  # type: ignore[attr-defined]
            "resolve_and_validate should be called on beam VB"
        )

    def test_calls_clear_then_resolve_on_all_slabs(self) -> None:
        p = Pavement()
        slab1 = _make_slab_double("LA")
        slab2 = _make_slab_double("LB")
        p.add_slab(slab1)
        p.add_slab(slab2)

        p.validate()

        assert "clear_resolved:LA" in slab1.calls, (  # type: ignore[attr-defined]
            "clear_resolved should be called on slab LA"
        )
        assert "resolve_and_validate:LA" in slab1.calls, (  # type: ignore[attr-defined]
            "resolve_and_validate should be called on slab LA"
        )
        assert "clear_resolved:LB" in slab2.calls, (  # type: ignore[attr-defined]
            "clear_resolved should be called on slab LB"
        )
        assert "resolve_and_validate:LB" in slab2.calls, (  # type: ignore[attr-defined]
            "resolve_and_validate should be called on slab LB"
        )


# ---------------------------------------------------------------------------
# TestPreSizeBeams
# ---------------------------------------------------------------------------


class TestPreSizeBeams:
    """pre_size_beams invokes beam.pre_size on every beam."""

    def test_calls_pre_size_on_all_beams(self) -> None:
        p = Pavement()
        beam1 = _make_beam_double("VA")
        beam2 = _make_beam_double("VB")
        p.add_beam(beam1)
        p.add_beam(beam2)

        p.pre_size_beams()

        assert "pre_size:VA" in beam1.calls, "pre_size should be called on beam VA"  # type: ignore[attr-defined]
        assert "pre_size:VB" in beam2.calls, "pre_size should be called on beam VB"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# TestLoadBeamSpans
# ---------------------------------------------------------------------------


class TestLoadBeamSpans:
    """load_beam_spans invokes beam.load_spans on every beam."""

    def test_calls_load_spans_on_all_beams(self) -> None:
        p = Pavement()
        beam1 = _make_beam_double("VA")
        beam2 = _make_beam_double("VB")
        p.add_beam(beam1)
        p.add_beam(beam2)

        p.load_beam_spans()

        assert "load_spans:VA" in beam1.calls, "load_spans should be called on beam VA"  # type: ignore[attr-defined]
        assert "load_spans:VB" in beam2.calls, "load_spans should be called on beam VB"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# TestElementIdCounters
# ---------------------------------------------------------------------------


def _auto_id_beam() -> ContinuousBeam:
    """Build a minimal beam with a counter-generated id."""
    wall = WallDefinition(
        structural=False,
        masonry_type="hollow concrete block",
        nominal_thickness=14,
        coating_thickness=1,
    )
    return ContinuousBeam(["P1", "P2"], "P1", 16, Alignment.CENTER, wall)


class TestElementIdCounters:
    """Each pavement restarts the auto-generated element ids."""

    def test_new_pavement_restarts_element_ids(self) -> None:
        Pillar(0, 0, 20, 30)
        _auto_id_beam()
        Slab(("PA", "PB", "PC", "PD"), "Bedrooms")  # advance every counter

        Pavement()

        assert Pillar(0, 0, 20, 30).id == "P1", "pillar ids should restart at P1"
        assert _auto_id_beam().id == "V1", "beam ids should restart at V1"
        assert Slab(("PA", "PB", "PC", "PD"), "Bedrooms").id == "L1", (
            "slab ids should restart at L1"
        )

    def test_reset_element_id_counters_restarts_ids(self) -> None:
        Pillar(0, 0, 20, 30)
        Pillar(0, 0, 20, 30)
        reset_element_id_counters()
        assert Pillar(0, 0, 20, 30).id == "P1", (
            "the next pillar after a reset should be P1"
        )


# ---------------------------------------------------------------------------
# TestPreSizeSlabs
# ---------------------------------------------------------------------------


class TestPreSizeSlabs:
    """pre_size_slabs loops until every slab returns True (stable)."""

    def test_stable_immediately_exits_in_one_pass(self) -> None:
        p = Pavement()
        call_count: list[int] = [0]

        def _counting_pre_size(registry: dict[str, Pillar]) -> bool:
            call_count[0] += 1
            return True  # stable on first call

        slab = _make_slab_double("L1")
        slab.pre_size = _counting_pre_size  # type: ignore[attr-defined]
        p.add_slab(slab)

        p.pre_size_slabs()

        assert call_count[0] == 1, (
            "pre_size should be called exactly once when stable immediately"
        )

    def test_unstable_then_stable_takes_two_passes(self) -> None:
        p = Pavement()
        call_count: list[int] = [0]
        results = [False, True]

        def _scripted_pre_size(registry: dict[str, Pillar]) -> bool:
            call_count[0] += 1
            return results.pop(0)

        slab = _make_slab_double("L1")
        slab.pre_size = _scripted_pre_size  # type: ignore[attr-defined]
        p.add_slab(slab)

        p.pre_size_slabs()

        assert call_count[0] == 2, (
            "pre_size should be called twice when unstable on first pass"
        )

    def test_two_slabs_both_must_be_stable_to_exit(self) -> None:
        """Loop does not exit while any slab is False or None."""
        p = Pavement()
        calls_a: list[int] = [0]
        calls_b: list[int] = [0]

        results_a = [False, True]  # unstable pass 1, stable pass 2
        results_b = [False, True]  # unstable pass 1, stable pass 2

        def _pre_size_a(registry: dict[str, Pillar]) -> bool:
            calls_a[0] += 1
            return results_a.pop(0)

        def _pre_size_b(registry: dict[str, Pillar]) -> bool:
            calls_b[0] += 1
            return results_b.pop(0)

        slab_a = _make_slab_double("LA")
        slab_b = _make_slab_double("LB")
        slab_a.pre_size = _pre_size_a  # type: ignore[attr-defined]
        slab_b.pre_size = _pre_size_b  # type: ignore[attr-defined]
        p.add_slab(slab_a)
        p.add_slab(slab_b)

        p.pre_size_slabs()

        assert calls_a[0] == 2, "slab A should be pre_sized twice"
        assert calls_b[0] == 2, "slab B should be pre_sized twice"

    def test_validates_lowered_after_sizing(self) -> None:
        """validate_lowered runs once per slab, after the last pre_size pass."""
        p = Pavement()
        log: list[str] = []
        slab = _make_slab_double("L1")
        slab.pre_size = lambda registry: log.append("pre_size") or True  # type: ignore[attr-defined]  # pyright: ignore[reportUnknownLambdaType]
        slab.validate_lowered = lambda: log.append("validate_lowered")  # type: ignore[attr-defined]
        p.add_slab(slab)

        p.pre_size_slabs()

        assert log == ["pre_size", "validate_lowered"], (
            "validate_lowered should run once, after pre-sizing"
        )

    def test_validate_lowered_error_propagates(self) -> None:
        p = Pavement()
        slab = _make_slab_double("L1")

        def _raise() -> None:
            raise ValueError("lowered too much")

        slab.validate_lowered = _raise  # type: ignore[attr-defined]
        p.add_slab(slab)

        with pytest.raises(ValueError, match="lowered too much"):
            p.pre_size_slabs()

    def test_non_converging_sizing_raises_after_max_passes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A slab that never stabilizes stops the loop at the pass cap"""
        monkeypatch.setattr(pavement_module, "MAX_SLAB_PRE_SIZE_PASSES", 3)
        p = Pavement()
        calls: list[int] = [0]

        def _oscillating_pre_size(registry: dict[str, Pillar]) -> bool:
            calls[0] += 1
            return False  # always resized

        unstable = _make_slab_double("LU")
        stable = _make_slab_double("LS")
        unstable.pre_size = _oscillating_pre_size  # type: ignore[attr-defined]
        stable.pre_size = lambda registry: True  # type: ignore[attr-defined]  # pyright: ignore[reportUnknownLambdaType]
        p.add_slab(unstable)
        p.add_slab(stable)

        with pytest.raises(ValueError, match=r"after 3 passes; still resizing: LU\.$"):
            p.pre_size_slabs()
        assert calls[0] == 3, "pre_size should run exactly once per allowed pass"


# ---------------------------------------------------------------------------
# TestUnloadSlabsOnBeams
# ---------------------------------------------------------------------------


class TestUnloadSlabsOnBeams:
    """unload_slabs_on_beams invokes slab.unload_on_supporting_spans on every slab."""

    def test_calls_unload_on_all_slabs(self) -> None:
        p = Pavement()
        slab1 = _make_slab_double("LA")
        slab2 = _make_slab_double("LB")
        p.add_slab(slab1)
        p.add_slab(slab2)

        p.unload_slabs_on_beams()

        assert "unload_on_supporting_spans:LA" in slab1.calls, (  # type: ignore[attr-defined]
            "unload should be called on slab LA"
        )
        assert "unload_on_supporting_spans:LB" in slab2.calls, (  # type: ignore[attr-defined]
            "unload should be called on slab LB"
        )


# ---------------------------------------------------------------------------
# TestDimensionBeams
# ---------------------------------------------------------------------------


class TestDimensionBeams:
    """dimension_beams invokes beam.dimension on every beam."""

    def test_calls_dimension_on_all_beams(self) -> None:
        p = Pavement()
        beam1 = _make_beam_double("VA")
        beam2 = _make_beam_double("VB")
        p.add_beam(beam1)
        p.add_beam(beam2)

        p.dimension_beams()

        assert "dimension:VA" in beam1.calls, "dimension should be called on beam VA"  # type: ignore[attr-defined]
        assert "dimension:VB" in beam2.calls, "dimension should be called on beam VB"  # type: ignore[attr-defined]


class TestDetailBeams:
    """detail_beams invokes beam.detail on every beam."""

    def test_calls_detail_on_all_beams(self) -> None:
        p = Pavement()
        beam1 = _make_beam_double("VA")
        beam2 = _make_beam_double("VB")
        p.add_beam(beam1)
        p.add_beam(beam2)

        p.detail_beams()

        assert "detail:VA" in beam1.calls, "detail should be called on beam VA"  # type: ignore[attr-defined]
        assert "detail:VB" in beam2.calls, "detail should be called on beam VB"  # type: ignore[attr-defined]

    def test_identical_bars_share_a_mark_across_beams(self) -> None:
        p = Pavement()
        first, second = _make_beam_double("VA"), _make_beam_double("VB")
        detailings = {
            "VA": _make_detailing("VA", _make_bar(300), _make_bar(400)),
            "VB": _make_detailing("VB", _make_bar(400), _make_bar(250)),
        }
        first.detail = lambda: detailings["VA"]  # type: ignore[method-assign]
        second.detail = lambda: detailings["VB"]  # type: ignore[method-assign]
        p.add_beam(first)
        p.add_beam(second)

        p.detail_beams()

        marks = {
            beam_id: [bar.mark for bar in detailing.bars]
            for beam_id, detailing in detailings.items()
        }
        assert marks == {"VA": ["N1", "N2"], "VB": ["N2", "N3"]}, (
            "The 400 cm bar should keep N2 in the second beam"
        )

    def test_detailing_again_restarts_at_n1(self) -> None:
        p = Pavement()
        beam = _make_beam_double("VA")
        beam.detail = lambda: _make_detailing("VA", _make_bar(300))  # type: ignore[method-assign]
        p.add_beam(beam)

        p.detail_beams()
        first_registry = p.mark_registry
        p.detail_beams()

        assert p.mark_registry is not first_registry, "A new registry is built"
        assert p.mark_registry.mark_for(bar_key(_make_bar(300))) == "N1", (
            "Numbering starts over at N1"
        )


# ---------------------------------------------------------------------------
# TestPrintBeamReports
# ---------------------------------------------------------------------------


class TestPrintBeamReports:
    """print_beam_reports prints every beam's report to stdout."""

    def test_prints_report_of_every_beam(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        p = Pavement()
        p.add_beam(_make_beam_double("VA"))
        p.add_beam(_make_beam_double("VB"))

        p.print_beam_reports()

        output = capsys.readouterr().out
        assert "report:VA" in output, "should print beam VA's report"
        assert "report:VB" in output, "should print beam VB's report"
        assert output.index("report:VA") < output.index("report:VB"), (
            "reports should follow beam insertion order"
        )

    def test_prints_detailing_report_after_beam_report(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        p = Pavement()
        beam = _make_beam_double("VA")
        beam.detailing = types.SimpleNamespace(  # type: ignore[assignment]
            report=lambda: "detailing:VA", bars=[], clamps=[], stirrups=[]
        )
        p.add_beam(beam)

        p.print_beam_reports()

        output = capsys.readouterr().out
        assert "detailing:VA" in output, "should print the beam's detailing report"
        assert output.index("report:VA") < output.index("detailing:VA"), (
            "the detailing report should follow the beam report"
        )

    def test_prints_pavement_schedule_last(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        p = Pavement()
        for beam_id in ("VA", "VB"):
            beam = _make_beam_double(beam_id)
            beam.detailing = _make_detailing(beam_id, _make_bar(300))
            p.add_beam(beam)
            MarkRegistry().assign(beam.detailing)

        p.print_beam_reports()

        output = capsys.readouterr().out
        lines = output.splitlines()
        title = lines.index("Bar schedule — pavement")
        assert output.index("report:VB") < output.index("Bar schedule — pavement"), (
            "The pavement schedule comes after the beam reports"
        )
        assert lines[title + 2].split() == ["N1", "bar", "φ10", "4", "300", "1200"], (
            "2 bars in each of the two beams add up under one mark"
        )

    def test_prints_nothing_without_beams(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        p = Pavement()
        capsys.readouterr()  # discard the logger's initialization line

        p.print_beam_reports()

        assert capsys.readouterr().out == "", "no beams should print nothing"


# ---------------------------------------------------------------------------
# TestResolve (wiring test)
# ---------------------------------------------------------------------------


class TestResolve:
    """resolve runs the full pipeline in the expected order without error."""

    def test_resolve_runs_all_steps(self) -> None:
        p = Pavement()
        log: list[str] = []

        beam = _make_beam_double("VA")
        beam.calls = log  # type: ignore[attr-defined]
        beam.clear_resolved = lambda: log.append("clear_resolved")  # type: ignore[attr-defined]
        beam.resolve_and_validate = lambda r: log.append("resolve_and_validate")  # type: ignore[attr-defined]
        beam.pre_size = lambda r: log.append("pre_size_beam")  # type: ignore[attr-defined]
        beam.load_spans = lambda: log.append("load_spans")  # type: ignore[attr-defined]
        beam.dimension = lambda r: log.append("dimension")  # type: ignore[attr-defined]

        def detail() -> DetailingBeam:
            log.append("detail")
            return _make_detailing("VA")

        beam.detail = detail  # type: ignore[method-assign]

        slab_log: list[str] = []
        slab = _make_slab_double("LA")
        slab.calls = slab_log  # type: ignore[attr-defined]
        slab.clear_resolved = lambda: slab_log.append("clear_resolved")  # type: ignore[attr-defined]
        slab.resolve_and_validate = lambda *a: slab_log.append("resolve_and_validate")  # type: ignore[attr-defined]
        slab.pre_size = lambda r: True  # type: ignore[attr-defined]
        slab.unload_on_supporting_spans = lambda r: slab_log.append("unload")  # type: ignore[attr-defined]

        p.add_beam(beam)
        p.add_slab(slab)

        p.resolve()  # should not raise

        # Beam pipeline: clear → resolve → pre_size → load_spans → dimension
        assert "clear_resolved" in log, "validate should call clear_resolved on beam"
        assert "resolve_and_validate" in log, (
            "validate should call resolve_and_validate on beam"
        )
        assert "pre_size_beam" in log, "pre_size_beams should call beam.pre_size"
        assert "load_spans" in log, "load_beam_spans should call beam.load_spans"
        assert "dimension" in log, "dimension_beams should call beam.dimension"
        assert log.index("dimension") < log.index("detail"), (
            "detail_beams should run after the beams are dimensioned"
        )

        # Slab pipeline: clear → resolve → unload
        assert "clear_resolved" in slab_log, (
            "validate should call clear_resolved on slab"
        )
        assert "resolve_and_validate" in slab_log, (
            "validate should call resolve_and_validate on slab"
        )
        assert "unload" in slab_log, (
            "unload_slabs_on_beams should call slab.unload_on_supporting_spans"
        )


# ---------------------------------------------------------------------------
# TestResolveKeepsResults — one real end-to-end resolve
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def resolved_single_panel() -> Pavement:
    """Resolve a real 5 × 4 m single-slab pavement: 4 pillars, 4 perimeter beams, 1 slab.

    Module-scoped: the resolve is slow and the tests only read its results.
    """
    corners = [
        Pillar(x=0, y=0, width=20, depth=25),
        Pillar(x=500, y=0, width=30, depth=25),
        Pillar(x=0, y=400, width=20, depth=35),
        Pillar(x=500, y=400, width=30, depth=35),
    ]
    bottom_left, bottom_right, top_left, top_right = corners
    pavement = Pavement()
    for pillar in corners:
        pavement.add_pillar(pillar)
    wall = WallDefinition(False, "hollow concrete block", 14, 1)
    for ids, alignment in [
        ([bottom_left.id, bottom_right.id], Alignment.BOTTOM),
        ([top_left.id, top_right.id], Alignment.TOP),
        ([bottom_left.id, top_left.id], Alignment.LEFT),
        ([bottom_right.id, top_right.id], Alignment.RIGHT),
    ]:
        pavement.add_beam(ContinuousBeam(ids, ids[0], 16, alignment, wall))
    pavement.add_slab(
        Slab(corner_pillar_ids=tuple(p.id for p in corners), local="Bedrooms")  # type: ignore[arg-type]
    )
    pavement.resolve()
    return pavement


class TestResolveKeepsResults:
    """resolve() leaves the results the GUI reads on the elements."""

    def test_beams_keep_analysis_and_calculators(
        self, resolved_single_panel: Pavement
    ) -> None:
        for beam in resolved_single_panel.beams.values():
            assert beam.analysis is not None, f"{beam.id} should keep its analysis"
            assert beam.rebar_calculators, f"{beam.id} should keep its calculators"
            positions = [c.bending_moment_position for c in beam.rebar_calculators]
            assert positions == sorted(positions), (
                f"{beam.id} calculators should be ordered left to right"
            )

    def test_beams_keep_detailing(self, resolved_single_panel: Pavement) -> None:
        for beam in resolved_single_panel.beams.values():
            assert beam.detailing is not None, f"{beam.id} should keep its detailing"
            assert beam.detailing.beam_id == beam.id, (
                f"{beam.id} detailing should name its beam"
            )
            assert beam.detailing.bars, f"{beam.id} detailing should have bars"

    def test_every_item_is_marked(self, resolved_single_panel: Pavement) -> None:
        for beam in resolved_single_panel.beams.values():
            detailing = cast(DetailingBeam, beam.detailing)
            items = [*detailing.bars, *detailing.clamps, *detailing.stirrups]
            assert all(item.mark is not None for item in items), (
                f"{beam.id} bars, clamps and stirrups should all have a mark"
            )

    def test_same_mark_means_same_bar(self, resolved_single_panel: Pavement) -> None:
        keys: dict[str, set[BarKey]] = {}
        for beam in resolved_single_panel.beams.values():
            for bar in cast(DetailingBeam, beam.detailing).bars:
                keys.setdefault(cast(str, bar.mark), set()).add(bar_key(bar))
        assert all(len(bar_keys) == 1 for bar_keys in keys.values()), (
            "Each mark should stand for one bar across the pavement"
        )

    def test_spans_keep_characteristic_shear(
        self, resolved_single_panel: Pavement
    ) -> None:
        for beam in resolved_single_panel.beams.values():
            for span in beam.spans:
                assert span.characteristic_shear_force > 0, (
                    f"{beam.id} spans should keep a positive Vk (kN)"
                )

    def test_slab_keeps_passing_deflection_check(
        self, resolved_single_panel: Pavement
    ) -> None:
        slab = next(iter(resolved_single_panel.slabs.values()))
        assert slab.deflection_check is not None, "slab should keep its check"
        assert slab.deflection_check.passes, "the kept check should pass"
        assert slab.deflection_check.height == slab.thickness, (
            "the check should be at the final thickness (cm)"
        )
        assert slab.deflection_support_case in range(1, 10), (
            "support case should be one of Carvalho's cases 1-9"
        )
