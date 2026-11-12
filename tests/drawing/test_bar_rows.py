"""Tests for src/drawing/bar_rows.py: bar rows, packing and lap marks."""

from collections.abc import Sequence

import pytest

from src.detailing.detailing_beam import DetailingBeam
from src.drawing.bar_rows import (
    BarRows,
    PlacedItem,
    bar_rows,
    boxes_overlap,
    lap_marks,
    row_items,
)
from src.drawing.config import DrawingConfig
from src.drawing.geometry import hook_path, overlap_pairs
from src.drawing.layers import DIMENSION, LAP, TEXT
from src.drawing.layout import beam_content, pillar_bottom
from src.drawing.primitives import Line, Polyline, Text
from src.pavement_elements.pavement import Pavement
from tests.drawing.helpers import close, detailings
from tests.drawing.v5 import bar

CONFIG = DrawingConfig()


def _rows(beam: DetailingBeam) -> BarRows:
    return bar_rows(beam, pillar_bottom(beam, CONFIG), CONFIG)


def _marks_by_row(placed: Sequence[PlacedItem]) -> list[list[str]]:
    """Return the marks on each row, top row first"""
    rows: dict[int, list[str]] = {}
    for item in placed:
        source = item.item.bar or item.item.clamps
        assert source is not None
        rows.setdefault(item.row, []).append(str(source.mark))
    return [rows[row] for row in sorted(rows)]


def _check_packing(beam: DetailingBeam, rows: BarRows) -> None:
    """Assert the packing rules of spec §6.5 on both faces"""
    for is_bottom, placed in ((False, rows.top), (True, rows.bottom)):
        expected = row_items(beam, is_bottom)
        assert [item.item for item in placed] == expected, (
            f"{beam.beam_id}: every item placed once, in group order"
        )
        for index, first in enumerate(placed):
            for second in placed[index + 1 :]:
                assert not any(
                    boxes_overlap(a, b) for a in first.boxes for b in second.boxes
                ), f"{beam.beam_id}: two items of a face cross each other"
        groups = sorted({item.item.group for item in placed})
        for upper, lower in zip(groups, groups[1:], strict=False):
            upper_rows = [item.row for item in placed if item.item.group == upper]
            lower_rows = [item.row for item in placed if item.item.group == lower]
            assert max(upper_rows) < min(lower_rows), (
                f"{beam.beam_id}: each group starts on a new row under the last"
            )
        for item in placed:
            if is_bottom:
                inside = all(box[3] < rows.separator_y for box in item.boxes)
            else:
                inside = all(box[1] > rows.separator_y for box in item.boxes)
            assert inside, f"{beam.beam_id}: the separator runs between the faces"


class TestPacking:
    """Items are placed on the first free row of their group."""

    def test_v5_rows(self, v5: DetailingBeam) -> None:
        rows = _rows(v5)
        assert _marks_by_row(rows.top) == [
            ["N1", "N3", "N6", "N8"],
            ["N2", "N5", "N7"],
            ["N4"],
        ], "Main bars, construction bars, then the second layer"
        assert _marks_by_row(rows.bottom) == [
            ["N10", "N13"],
            ["N12"],
            ["N11"],
            ["N14"],
        ], "The lapped N12 goes under N10 and N13; clamps last"

    def test_v5_rules(self, v5: DetailingBeam) -> None:
        _check_packing(v5, _rows(v5))

    def test_separator_between_faces(self, v5: DetailingBeam) -> None:
        rows = _rows(v5)
        top_low = min(box[1] for item in rows.top for box in item.boxes)
        bottom_high = max(box[3] for item in rows.bottom for box in item.boxes)
        assert bottom_high < rows.separator_y < top_low, (
            "The separator splits the faces"
        )

    def test_rows_pitch(self, v5: DetailingBeam) -> None:
        rows = _rows(v5)
        top_y = pillar_bottom(v5, CONFIG) - CONFIG.paper(22.0)
        assert {item.y for item in rows.top} == {top_y, top_y - 50.0, top_y - 100.0}, (
            "10 mm of paper between rows, the first one under the pillar names"
        )

    @pytest.mark.slow
    def test_t_concreto2(self, t_concreto2: Pavement) -> None:
        for beam in detailings(t_concreto2):
            _check_packing(beam, _rows(beam))


class TestRowItems:
    """How a bar run looks on its row."""

    def _placed(self, rows: BarRows, mark: str) -> PlacedItem:
        return next(
            item
            for item in (*rows.top, *rows.bottom)
            if item.item.bar is not None and item.item.bar.mark == mark
        )

    def test_hook_keeps_direction(self, v5: DetailingBeam) -> None:
        placed = self._placed(_rows(v5), "N8")
        path = next(i for i in placed.drawing.items if isinstance(i, Polyline))
        assert close(path.points[-1][1], placed.y - 66.0), (
            "The frame-node leg still goes down: 8 + 58 cm under the row"
        )

    def test_texts(self, v5: DetailingBeam) -> None:
        placed = self._placed(_rows(v5), "N1")
        texts = {i.text: i for i in placed.drawing.items if isinstance(i, Text)}
        assert set(texts) == {"102", "30", "2 N1 φ10 C=136"}, (
            "Straight length, hook tip and label"
        )
        assert texts["30"].rotation == 90.0, "The hook tip turns with the leg"
        assert texts["102"].layer == DIMENSION, "Lengths on the dimension layer"
        assert texts["2 N1 φ10 C=136"].layer == TEXT, "Labels on the text layer"

    def test_label_clears_leg(self, v5: DetailingBeam) -> None:
        placed = self._placed(_rows(v5), "N1")
        label = next(
            i
            for i in placed.drawing.items
            if isinstance(i, Text) and i.text.startswith("2 N1")
        )
        path = hook_path(bar(v5, "N1"), left=True)
        assert path is not None
        left_edge = min(x for x, _ in label.corners())
        assert left_edge >= path[2][0] + CONFIG.paper(1.5) - 1e-9, (
            "The label moves right of the leg it would cross"
        )

    def test_paper_marks(self, v5: DetailingBeam) -> None:
        rows = _rows(v5)
        for mark, paper_mark in (("N2", "(MONTAGEM)"), ("N4", "(2ª CAMADA)")):
            texts = [
                i.text
                for i in self._placed(rows, mark).drawing.items
                if isinstance(i, Text)
            ]
            assert paper_mark in texts, f"{mark} carries {paper_mark}"

    def test_clamp_u(self, v5: DetailingBeam) -> None:
        rows = _rows(v5)
        clamp = next(item for item in rows.bottom if item.item.clamps is not None)
        u = next(i for i in clamp.drawing.items if isinstance(i, Polyline))
        assert u.points == (
            (1167.0, clamp.y),
            (1207.0, clamp.y),
            (1207.0, clamp.y - 13.0),
            (1167.0, clamp.y - 13.0),
        ), "Bend at 1207, legs 40 cm toward −x, 13 cm apart"
        texts = [i.text for i in clamp.drawing.items if isinstance(i, Text)]
        assert texts == ["40", "13", "2 N14 φ6,3 C=93", "(GRAMPO)"], "Leg, width, label"


def _lap_texts(beam: DetailingBeam) -> list[Text]:
    """Return the texts of the lap dimensions of both faces"""
    rows = _rows(beam)
    marks = [
        *lap_marks(beam, False, rows.top, CONFIG).items,
        *lap_marks(beam, True, rows.bottom, CONFIG).items,
    ]
    return [item for item in marks if isinstance(item, Text)]


class TestLaps:
    """Each overlap is dimensioned between the rows of its two runs (§6.6)."""

    def test_one_mark_per_overlap(self, v5: DetailingBeam) -> None:
        drawing = beam_content(v5, CONFIG, tables=False)
        pairs = overlap_pairs(v5, False) + overlap_pairs(v5, True)
        laps = [i for i in drawing.items if isinstance(i, Line) and i.layer == LAP]
        assert len(laps) == 2 * len(pairs) == 16, "Two dashed limits per overlap"
        texts = [i.text for i in _lap_texts(v5)]
        assert sorted(texts) == ["20"] * 6 + ["30"] * 2, "One lap length per overlap"

    def test_lap_limits_join_rows(self, v5: DetailingBeam) -> None:
        rows = _rows(v5)
        laps = [i for i in rows.drawing.items if isinstance(i, Line) and i.layer == LAP]
        n10_n12 = [line for line in laps if line.start[0] in (415.0, 445.0)]
        heights = {item.item.bar.mark: item.y for item in rows.bottom if item.item.bar}
        assert {(line.start[1], line.end[1]) for line in n10_n12} == {
            (heights["N10"], heights["N12"])
        }, "From N10's row down to N12's"

    def test_lap_texts_clear_labels(self, v5: DetailingBeam) -> None:
        rows = _rows(v5)
        obstacles = [box for item in (*rows.top, *rows.bottom) for box in item.boxes]
        for item in _lap_texts(v5):
            xs, ys = zip(*item.corners(), strict=True)
            box = (min(xs), min(ys), max(xs), max(ys))
            assert not any(boxes_overlap(box, other) for other in obstacles), (
                f"Lap text {item.text} at {item.position} crosses a row item"
            )
