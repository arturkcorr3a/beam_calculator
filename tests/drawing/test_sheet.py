"""Tests for the sheet formats, the frame and the block of notes and title block (docs/especificacao-selo.md)."""

import pytest

from src.drawing.config import DrawingConfig
from src.drawing.layers import BLOCK_HEAVY, SHEET_FRAME, SHEET_FRAME_HEAVY
from src.drawing.primitives import Drawing, Image, Line, Polyline, Text
from src.drawing.sheet import (
    BLOCK_HEIGHT_MM,
    BLOCK_WIDTH_MM,
    FORMATS,
    BlockContent,
    SheetFitError,
    build_block,
    build_sheet,
    check_materials,
    choose_sheet,
    general_notes,
    sheet_number,
    sheet_title,
)
from tests.drawing.helpers import close

CONFIG = DrawingConfig()


def fmt(name: str, orientation: str = "paisagem"):
    return next(f for f in FORMATS if f.name == name and f.orientation == orientation)


def content(**changes: object) -> BlockContent:
    values: dict[str, object] = {
        "project": "Residência unifamiliar — Rua Exemplo, 123",
        "title": sheet_title("V3", 15, 40),
        "date": "12/11/2026",
        "sheet": sheet_number(3, 8),
        "notes": general_notes(25, "CA-50", "CA-60", "II", 3.0),
    }
    values.update(changes)
    return BlockContent(**values)  # type: ignore[arg-type]


def texts(drawing: Drawing) -> list[str]:
    return [item.text for item in drawing.items if isinstance(item, Text)]


def outline(drawing: Drawing) -> Drawing:
    """The lines of a drawing, without the texts, whose width is only estimated."""
    return Drawing([i for i in drawing.items if isinstance(i, (Line, Polyline))])


class TestRegions:
    """The free regions of spec §2.4."""

    @pytest.mark.parametrize(
        ("name", "orientation", "a", "b"),
        [
            ("A4", "paisagem", (247, 88), (67, 170)),
            ("A4", "retrato", (160, 175), None),
            ("A3", "paisagem", (370, 175), (190, 257)),
            ("A2", "paisagem", (544, 298), (364, 380)),
            ("A1", "paisagem", (791, 472), (611, 554)),
            ("A0", "paisagem", (1139, 719), (959, 801)),
        ],
    )
    def test_table(
        self,
        name: str,
        orientation: str,
        a: tuple[float, float],
        b: tuple[float, float] | None,
    ) -> None:
        regions = fmt(name, orientation).free_regions()
        assert regions["A"] == a, f"{name} {orientation}: region A of the spec"
        assert regions.get("B") == b, f"{name} {orientation}: region B of the spec"


class TestChoice:
    """The choice of the format, spec §2.4."""

    def test_smallest_fit(self) -> None:
        placement = choose_sheet(120, 80)
        assert (placement.format.name, placement.region) == ("A4", "A")

    def test_region_b_is_used(self) -> None:
        placement = choose_sheet(60, 160)
        assert (placement.format.name, placement.region) == ("A4", "B"), (
            "Tall and narrow: fits left of the block"
        )

    def test_next_format_when_too_big(self) -> None:
        placement = choose_sheet(340, 170)
        assert placement.format.name == "A3", "340 mm is over A4's 247 mm"

    def test_portrait_only_when_asked(self) -> None:
        assert choose_sheet(150, 170).format.name == "A3", "Landscape A4 is too short"
        placement = choose_sheet(150, 170, orientation="retrato")
        assert (placement.format.name, placement.format.orientation) == (
            "A4",
            "retrato",
        )

    def test_empty_corner_is_used(self) -> None:
        corner = [(0.0, 0.0, 300.0, 100.0), (0.0, 0.0, 100.0, 224.0)]
        assert choose_sheet(300, 224).format.name == "A2", "As a rectangle: A2"
        placement = choose_sheet(300, 224, boxes=corner)
        assert (placement.format.name, placement.region) == ("A3", "L"), (
            "Nothing reaches the block's corner: A3 holds it"
        )

    def test_corner_taken(self) -> None:
        in_block = [(0.0, 0.0, 300.0, 100.0), (250.0, 200.0, 300.0, 224.0)]
        assert choose_sheet(300, 224, boxes=in_block).format.name == "A2", (
            "An item over the block's place pushes the drawing to the next format"
        )

    def test_summary_takes_room_from_region_a(self) -> None:
        assert choose_sheet(300, 170).format.name == "A3", "Region A: 175 mm"
        placement = choose_sheet(300, 170, summary_mm=(60, 60))
        assert placement.format.name == "A2", "The summary shrinks region A by 65 mm"

    def test_summary_keeps_out_items(self) -> None:
        box = [(0.0, 0.0, 300.0, 100.0), (330.0, 100.0, 360.0, 160.0)]
        assert choose_sheet(360, 224, boxes=box).format.name == "A3"
        placement = choose_sheet(360, 224, boxes=box, summary_mm=(100, 60))
        assert placement.format.name == "A2", "An item in the summary's place"

    def test_nothing_fits(self) -> None:
        placement = choose_sheet(2000, 900)
        assert (placement.format.name, placement.overflow) == ("A0", True)

    def test_fixed_format(self) -> None:
        assert choose_sheet(100, 50, "A2").format.name == "A2", "Asked for A2"

    def test_fixed_too_small(self) -> None:
        with pytest.raises(SheetFitError, match="A4"):
            choose_sheet(300, 100, "A4")

    def test_unknown(self) -> None:
        with pytest.raises(ValueError, match="A5"):
            choose_sheet(10, 10, "A5")
        with pytest.raises(ValueError, match="retrato"):
            choose_sheet(10, 10, "A3", "retrato")


class TestNotes:
    """The general notes of spec §5.2."""

    def test_different_steels(self) -> None:
        notes = general_notes(25, "CA-50", "CA-60", "II", 3.0)
        assert notes[0] == "Concreto: C25 (fck = 25 MPa)."
        assert notes[1] == (
            "Aço: CA-50 nas barras longitudinais (fyk = 500 MPa); CA-60 nos "
            "estribos (fyk = 600 MPa)."
        )
        assert notes[2] == (
            "Classe de agressividade ambiental II — cobrimento nominal c = 3,0 cm."
        )
        assert len(notes) == 5

    def test_same_steel(self) -> None:
        notes = general_notes(30, "CA-50", "CA-50", "III", 4.0)
        assert notes[1] == "Aço: CA-50 (fyk = 500 MPa)."

    def test_unknown_steel(self) -> None:
        with pytest.raises(ValueError, match="CA-40"):
            general_notes(25, "CA-40", "CA-50", "II", 3.0)

    def test_title(self) -> None:
        assert sheet_title("V3", 15, 40) == "VIGA V3 (15×40) — DETALHAMENTO — PAV. TIPO"
        assert (
            sheet_title("v4", 14.5, 40)
            == "VIGA V4 (14,5×40) — DETALHAMENTO — PAV. TIPO"
        )

    def test_sheet_number(self) -> None:
        assert sheet_number(3, 8) == "03/08"

    def test_minimums(self) -> None:
        assert check_materials(25, "II", 3.0) == []
        assert len(check_materials(20, "II", 2.5)) == 2, "fck and cover below CAA II"
        assert "C40" in check_materials(30, "IV", 5.0)[0]


class TestBlock:
    """The 180 × 82 mm block of spec §3."""

    def test_size(self) -> None:
        x_min, y_min, x_max, y_max = outline(build_block(content(), CONFIG)).bounds()
        assert (x_min, y_max) == (0.0, 0.0), "Top left corner at the origin"
        assert close(CONFIG.on_paper(x_max - x_min), BLOCK_WIDTH_MM)
        assert close(CONFIG.on_paper(y_max - y_min), BLOCK_HEIGHT_MM)

    def test_same_size_at_any_scale(self) -> None:
        config = DrawingConfig(sheet_scale=100)
        x_min, _, x_max, _ = outline(build_block(content(), config)).bounds()
        assert close(config.on_paper(x_max - x_min), BLOCK_WIDTH_MM)

    def test_heavy_lines(self) -> None:
        drawing = build_block(content(), CONFIG)
        ys = sorted(
            -CONFIG.on_paper(item.start[1])
            for item in drawing.items
            if isinstance(item, Line) and item.layer == BLOCK_HEAVY
        )
        assert close(ys, [32.0, 75.0]), "Thick lines at y = 32 and y = 75"

    def test_fields(self) -> None:
        shown = texts(build_block(content(), CONFIG))
        for expected in (
            "NOTAS GERAIS",
            "VIGA V3 (15×40) — DETALHAMENTO — PAV. TIPO",
            "03/08",
            "R00",
            "FORMATO",
            "1:50 / 1:25",
            "Cotas em cm",
            "12/11/2026",
            "DOCUMENTO ACADÊMICO — NÃO VÁLIDO PARA EXECUÇÃO",
        ):
            assert expected in shown, f"{expected} on the block"

    def test_logo(self) -> None:
        images = [
            i for i in build_block(content(), CONFIG).items if isinstance(i, Image)
        ]
        assert len(images) == 1 and "vertical" in images[0].path
        assert close(CONFIG.on_paper(images[0].width), 36.0)
        assert close(CONFIG.on_paper(images[0].height), 39.0)
        no_logo = build_block(content(logo=None), CONFIG)
        assert not any(isinstance(i, Image) for i in no_logo.items)

    def test_long_project_is_cut(self) -> None:
        shown = texts(build_block(content(project="X" * 200), CONFIG))
        cut = [text for text in shown if text.startswith("XXX")]
        assert cut[0].endswith("…") and len(cut[0]) < 200

    def test_long_title_shrinks(self) -> None:
        title = sheet_title("V101a", 100, 100) + " " + "X" * 20
        block = build_block(content(title=title), CONFIG)
        heights = {
            round(CONFIG.on_paper(i.height), 1)
            for i in block.items
            if isinstance(i, Text) and i.text.startswith("VIGA")
        }
        assert heights == {3.0} or heights == {2.5}, "A long title takes a smaller size"

    def test_notes_fit_six_lines(self) -> None:
        long_notes = general_notes(25, "CA-50", "CA-60", "II", 3.0)
        block = build_block(content(notes=long_notes), CONFIG)
        note_ys = {
            round(CONFIG.on_paper(-i.position[1]), 3)
            for i in block.items
            if isinstance(i, Text)
            and i.position[0] > 0
            and -CONFIG.on_paper(i.position[1]) < 32
        }
        assert len(note_ys) <= 7, "Heading plus at most six note lines"
        assert max(note_ys) < 32.0, "Notes stay in their 32 mm"


class TestSheet:
    """The drawing on its sheet."""

    def drawing(self, width_mm: float, height_mm: float) -> Drawing:
        return Drawing(
            [
                Line(
                    (0.0, 0.0),
                    (CONFIG.paper(width_mm), CONFIG.paper(height_mm)),
                    "COTA",
                )
            ]
        )

    @pytest.mark.parametrize(
        ("name", "origin"),
        [
            ("A4", (107, 10)),
            ("A3", (230, 10)),
            ("A2", (404, 10)),
            ("A1", (651, 10)),
            ("A0", (999, 10)),
        ],
    )
    def test_block_position(self, name: str, origin: tuple[float, float]) -> None:
        config = DrawingConfig(sheet_format=name)
        sheet, _ = build_sheet(self.drawing(50, 50), content(), config)
        heavy = [
            i for i in sheet.items if isinstance(i, Polyline) and i.layer == BLOCK_HEAVY
        ]
        xs = [config.on_paper(x) for x, _ in heavy[0].points]
        ys = [config.on_paper(y) for _, y in heavy[0].points]
        assert close((min(xs), min(ys)), origin), f"{name}: spec §2.3 table"

    def test_paper_in_the_title_block(self) -> None:
        sheet, _ = build_sheet(self.drawing(100, 60), content(), CONFIG)
        assert "A4" in texts(sheet), "The format is written in the block"
        portrait = DrawingConfig(sheet_format="A4", sheet_orientation="retrato")
        sheet, _ = build_sheet(self.drawing(100, 60), content(), portrait)
        assert "A4 (retrato)" in texts(sheet), "The orientation of the portrait too"

    def test_frame_margins(self) -> None:
        sheet, placement = build_sheet(self.drawing(100, 60), content(), CONFIG)
        frame = next(
            i for i in sheet.items if isinstance(i, Polyline) and i.layer == SHEET_FRAME
        )
        xs = [CONFIG.on_paper(x) for x, _ in frame.points]
        ys = [CONFIG.on_paper(y) for _, y in frame.points]
        assert close((min(xs), min(ys), max(xs), max(ys)), (20, 10, 287, 200))
        assert sheet.paper_mm == (297, 210)
        assert placement.format.name == "A4"

    def test_big_sheets_have_a_heavy_frame(self) -> None:
        sheet, _ = build_sheet(
            self.drawing(100, 60), content(), DrawingConfig(sheet_format="A1")
        )
        layers = {i.layer for i in sheet.items if isinstance(i, Polyline)}
        assert SHEET_FRAME_HEAVY in layers and SHEET_FRAME not in layers

    def test_drawing_stays_clear_of_the_block(self) -> None:
        for width, height in ((240, 85), (65, 165), (360, 170), (700, 280)):
            sheet, placement = build_sheet(
                self.drawing(width, height), content(), CONFIG
            )
            fmt_ = placement.format
            line = next(
                i for i in sheet.items if isinstance(i, Line) and i.layer == "COTA"
            )
            xs = [CONFIG.on_paper(x) for x in (line.start[0], line.end[0])]
            ys = [CONFIG.on_paper(y) for y in (line.start[1], line.end[1])]
            block_left = fmt_.width_mm - 190
            block_top = 92  # y up
            over_block = max(xs) > block_left and min(ys) < block_top
            assert not over_block, f"{width}×{height} stays out of the block"
            assert min(xs) >= 30 - 1e-6 and max(xs) <= fmt_.width_mm - 20 + 1e-6
            assert min(ys) >= 20 - 1e-6 and max(ys) <= fmt_.height_mm - 20 + 1e-6

    def test_fixed_format_that_does_not_fit(self) -> None:
        with pytest.raises(SheetFitError):
            build_sheet(
                self.drawing(400, 100), content(), DrawingConfig(sheet_format="A4")
            )
