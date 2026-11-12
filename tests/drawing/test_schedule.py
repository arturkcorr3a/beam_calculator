"""Tests for the summary, legend and title block, and their place on the sheets."""

import datetime
from pathlib import Path

import pytest

from src.config import APP_CONFIG
from src.config_options import ExposureClass
from src.detailing.bar_schedule import build_schedule
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.quantities import build_quantities
from src.drawing.api import export_beam_dxf
from src.drawing.config import DrawingConfig
from src.drawing.layers import LAYERS
from src.drawing.layout import beam_content, build_beam_drawing
from src.drawing.primitives import Drawing, Line, Text
from src.drawing.schedule_layout import summary_table
from src.drawing.sheet_info import SheetInfo, read_sheet_info
from src.pavement_elements.pavement import Pavement
from src.properties.concrete import Concrete
from tests.drawing.helpers import detailings, read_dxf

CONFIG = DrawingConfig()
SHEET = SheetInfo("C30", "II", "t_demo", datetime.date(2026, 11, 7), 3, 8)


def _texts(drawing: Drawing) -> list[str]:
    return [item.text for item in drawing.items if isinstance(item, Text)]


class TestTables:
    """Materials summary (§6.9)."""

    def test_summary(self, v5: DetailingBeam) -> None:
        quantities = build_quantities([v5])
        texts = _texts(
            summary_table(
                "CA-50",
                quantities.steel,
                quantities.concrete_m3,
                quantities.formwork_m2,
                CONFIG,
            )
        )
        assert texts[:4] == ["RESUMO CA-50", "φ", "COMPR. (m)", "MASSA (kg)"], "Headers"
        assert "TOTAL" in texts, "A total row"
        ratio = round(quantities.beams[0].steel_mass_kg / quantities.concrete_m3)
        assert texts[-3:] == [
            "Concreto: 1,09 m³",
            "Fôrma: 13,6 m²",
            f"Taxa de aço: {ratio} kg/m³",
        ], "Concrete, formwork and steel ratio"

    def test_columns_fit_cells(self) -> None:
        drawing = summary_table("CA-50", [], 0.0, 0.0, CONFIG)
        header = next(
            item
            for item in drawing.items
            if isinstance(item, Text) and item.text == "COMPR. (m)"
        )
        corners = header.corners()
        assert corners[1][0] - corners[0][0] < CONFIG.paper(20.0), (
            "Header fits its column"
        )


class TestSheetInfo:
    """sheet_info.py reads APP_CONFIG (§6.11)."""

    def test_reads_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C40)
        monkeypatch.setattr(APP_CONFIG, "exposure_class", ExposureClass.SEVERE)
        info = read_sheet_info("t_concreto2")
        assert (info.concrete, info.exposure_class, info.pavement_name) == (
            "C40",
            "III",
            "t_concreto2",
        ), "Concrete class, exposure class in Roman numerals and the name"
        assert (info.sheet_number, info.sheet_total) == (1, 1), "One sheet by default"

    def test_only_module_reading_config(self) -> None:
        folder = Path(__file__).parents[2] / "src" / "drawing"
        readers = sorted(
            path.name
            for path in folder.glob("*.py")
            if "import APP_CONFIG" in path.read_text()
        )
        assert readers == ["sheet_info.py"], "Spec D8: one module reads APP_CONFIG"


class TestSheets:
    """The blocks on the beam sheet and on the pavement sheet."""

    def test_beam_sheet(self, v5: DetailingBeam) -> None:
        texts = _texts(build_beam_drawing(v5, CONFIG, sheet=SHEET))
        for expected in (
            "RESUMO CA-50",
            "LEGENDA",
            "VIGA V5 (19×50) — DETALHAMENTO — PAV. TIPO",
            "t_demo",
            "07/11/2026",
            "03/08",
            "Concreto: C30 (fck = 30 MPa).",
            "Aço: CA-50 (fyk = 500 MPa).",
            "NOTAS GERAIS",
            "R00",
        ):
            assert expected in texts, f"The beam sheet has {expected}"
        assert "QUADRO DE FERROS" not in texts, "No bar schedule"

    def test_content_has_no_block(self, v5: DetailingBeam) -> None:
        texts = _texts(beam_content(v5, CONFIG))
        assert "NOTAS GERAIS" not in texts, "Notes belong to the sheet"
        assert "LEGENDA" in texts, "The legend stays with the drawing"
        assert "RESUMO CA-50" not in texts, "The summary goes above the block"

    def test_summary_above_the_block(self, v5: DetailingBeam) -> None:
        drawing = build_beam_drawing(v5, CONFIG, sheet=SHEET)
        assert drawing.paper_mm is not None
        title = next(
            i for i in drawing.items if isinstance(i, Text) and i.text == "RESUMO CA-50"
        )
        x_mm = CONFIG.on_paper(title.position[0])
        y_mm = CONFIG.on_paper(title.position[1])
        assert x_mm > drawing.paper_mm[0] - 190, "Over the block, on the right"
        assert y_mm > 92 + 5, "Above the block and its 5 mm gap"
        right = max(
            CONFIG.on_paper(i.start[0])
            for i in drawing.items
            if isinstance(i, Line)
            and i.layer == "QUADRO"
            and CONFIG.on_paper(i.start[1]) > 97
        )
        assert right <= drawing.paper_mm[0] - 10 - 5 + 1e-6, "5 mm off the frame"

    def test_paper(self, v5: DetailingBeam) -> None:
        drawing = build_beam_drawing(v5, CONFIG, sheet=SHEET)
        assert drawing.paper_mm is not None, "The sheet knows its paper"
        assert drawing.paper_mm[0] > drawing.paper_mm[1], "Landscape by default"

    def test_layers_known(self, v5: DetailingBeam) -> None:
        drawing = build_beam_drawing(v5, CONFIG, sheet=SHEET)
        assert set(drawing.layers()) <= set(LAYERS), "Every primitive on a table layer"


@pytest.mark.slow
class TestDxfRoundTrip:
    """Spec §11 test_dxf_roundtrip on t_concreto2."""

    def test_beams(self, t_concreto2: Pavement, tmp_path: Path) -> None:
        for beam in detailings(t_concreto2):
            doc = read_dxf(export_beam_dxf(beam, tmp_path / f"{beam.beam_id}.dxf"))
            assert not doc.audit().has_errors, f"{beam.beam_id}: clean audit"
            texts = {
                entity.dxf.text
                for entity in doc.modelspace()
                if entity.dxftype() == "TEXT"
            }
            words = {word for text in texts for word in text.split()}
            marks = {row.mark for row in build_schedule([beam])}
            assert marks <= words, f"{beam.beam_id}: every mark is labelled"
            layers = {entity.dxf.layer for entity in doc.modelspace()}
            assert layers <= set(LAYERS), f"{beam.beam_id}: only the table's layers"
