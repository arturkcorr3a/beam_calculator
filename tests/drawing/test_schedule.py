"""Tests for the schedule, summary, notes and title block, and their place on the sheets."""

import datetime
from pathlib import Path

import pytest

from src.config import APP_CONFIG
from src.config_options import ExposureClass
from src.detailing.bar_schedule import build_schedule
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.quantities import build_quantities
from src.drawing.api import export_beam_dxf, export_pavement_dxf
from src.drawing.config import DrawingConfig
from src.drawing.layers import LAYERS
from src.drawing.layout import build_beam_drawing, build_pavement_drawing
from src.drawing.primitives import Drawing, Text
from src.drawing.schedule_layout import (
    note_lines,
    schedule_table,
    summary_table,
    title_block,
)
from src.drawing.sheet_info import SheetInfo, read_sheet_info
from src.pavement_elements.pavement import Pavement
from src.properties.concrete import Concrete
from tests.drawing.helpers import close, detailings, fake_pavement, read_dxf

CONFIG = DrawingConfig()
SHEET = SheetInfo("C30", "II", "t_demo", datetime.date(2026, 11, 7), "V5.dxf")


def _texts(drawing: Drawing) -> list[str]:
    return [item.text for item in drawing.items if isinstance(item, Text)]


class TestTables:
    """Bar schedule and materials summary (§6.9)."""

    def test_schedule(self, v5: DetailingBeam) -> None:
        texts = _texts(schedule_table(build_schedule([v5]), CONFIG))
        assert texts[:6] == [
            "QUADRO DE FERROS",
            "POS",
            "φ (mm)",
            "QUANT",
            "C. UNIT (cm)",
            "C. TOTAL (cm)",
        ], "Title and headers"
        assert texts[6:11] == ["N1", "10", "2", "136", "272"], "First row"
        assert "10400" in texts, "80 N9 stirrups × 130 cm"
        marks = [text for text in texts if text.startswith("N")]
        assert marks == [f"N{n}" for n in range(1, 15)], "One row per mark, in order"

    def test_schedule_width(self, v5: DetailingBeam) -> None:
        drawing = schedule_table(build_schedule([v5]), CONFIG)
        x_min, _, x_max, _ = drawing.bounds()
        assert x_max - x_min >= CONFIG.paper(13 + 13 + 15 + 24 + 26) - 1e-9, (
            "At least the spec's column widths"
        )

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


class TestNotes:
    """Notes of §6.10."""

    def test_full(self) -> None:
        assert note_lines("CA-50", "C30", "II", [2.5]) == [
            "1. Medidas em cm; bitolas (φ) em mm.",
            "2. Aço CA-50; concreto C30, classe de agressividade II.",
            "3. Cobrimento nominal c = 2,5 cm.",
            "4. Comprimentos de corte líquidos, sem perdas.",
            "5. Estribos fechados de 2 ramos, ganchos a 135°.",
        ], "The five notes"

    def test_missing_data_left_out(self) -> None:
        assert note_lines("CA-50", None, None, [2.5])[1] == "2. Aço CA-50.", (
            "Only the steel"
        )
        assert note_lines("CA-50", None, "II", [2.5])[1] == (
            "2. Aço CA-50; classe de agressividade II."
        ), "Steel and exposure class"

    def test_distinct_covers(self) -> None:
        assert note_lines("CA-50", "C30", "II", [3.0, 2.5, 2.5, 4.0])[2] == (
            "3. Cobrimentos nominais c = 2,5, 3 e 4 cm."
        ), "Each distinct cover once"


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
        assert info.file_name == "", "No file on screen"

    def test_only_module_reading_config(self) -> None:
        folder = Path(__file__).parents[2] / "src" / "drawing"
        readers = sorted(
            path.name
            for path in folder.glob("*.py")
            if "import APP_CONFIG" in path.read_text()
        )
        assert readers == ["sheet_info.py"], "Spec D8: one module reads APP_CONFIG"


class TestTitleBlock:
    """The title block of §6.11."""

    def test_fields(self) -> None:
        drawing = title_block(
            "VIGA V5",
            [("PAVIMENTO", "t_demo"), ("ARQUIVO", "")],
            "07/11/2026",
            "",
            CONFIG,
        )
        assert _texts(drawing) == [
            "VIGA V5",
            "PAVIMENTO",
            "t_demo",
            "ARQUIVO",
            "",
            "07/11/2026",
        ], "Title, label over value, date"
        x_min, _, x_max, _ = drawing.bounds()
        assert close(x_max - x_min, CONFIG.paper(44.0)), "44 mm wide"

    def test_grows_for_long_text(self) -> None:
        drawing = title_block("T", [("SEÇÃO", "x" * 40)], "", "FOLHA 1/1", CONFIG)
        x_min, _, x_max, _ = drawing.bounds()
        assert x_max - x_min > CONFIG.paper(44.0), "Wider when a text needs it"


class TestSheets:
    """The blocks on the beam sheet and on the pavement sheet."""

    def test_beam_sheet(self, v5: DetailingBeam) -> None:
        texts = _texts(build_beam_drawing(v5, CONFIG, sheet=SHEET))
        for expected in (
            "QUADRO DE FERROS",
            "RESUMO CA-50",
            "NOTAS",
            "LEGENDA",
            "VIGA V5",
        ):
            assert expected in texts, f"The beam sheet has {expected}"
        assert "19 × 50 cm · CA-50 · c 2,5" in texts, "Section field"
        assert "V5.dxf" in texts, "File name"
        assert "07/11/2026" in texts, "Date"
        assert "Elevação 1:50 · Cortes 1:25" in texts, "Scales"

    def test_pavement_part_has_no_blocks(self, v5: DetailingBeam) -> None:
        texts = _texts(build_beam_drawing(v5, CONFIG, standalone=False))
        assert "QUADRO DE FERROS" not in texts, "No schedule per beam on the pavement"
        assert "NOTAS" not in texts, "No notes per beam on the pavement"

    def test_pavement_sheet(self, v5: DetailingBeam) -> None:
        drawing = build_pavement_drawing(fake_pavement(v5), CONFIG, sheet=SHEET)
        texts = _texts(drawing)
        assert texts.count("QUADRO DE FERROS") == 1, "One general schedule"
        for expected in ("VIGAS DO PAVIMENTO", "FOLHA 1/1", "t_demo", "CA-50 · c 2,5"):
            assert expected in texts, f"The pavement sheet has {expected}"

    def test_layers_known(self, v5: DetailingBeam) -> None:
        drawing = build_beam_drawing(v5, CONFIG, sheet=SHEET)
        assert set(drawing.layers()) <= set(LAYERS), "Every primitive on a table layer"


@pytest.mark.slow
class TestDxfRoundTrip:
    """Spec §11 test_dxf_roundtrip on t_concreto2."""

    def test_pavement(self, t_concreto2: Pavement, tmp_path: Path) -> None:
        path = export_pavement_dxf(t_concreto2, tmp_path / "t_concreto2.dxf")
        doc = read_dxf(path)
        assert not doc.audit().has_errors, "Clean audit"
        assert doc.header["$INSUNITS"] == 5, "Units in cm"
        texts = {
            entity.dxf.text for entity in doc.modelspace() if entity.dxftype() == "TEXT"
        }
        marks = {row.mark for row in t_concreto2.bar_schedule()}
        assert marks <= texts, "Every mark of the schedule is a TEXT"
        assert "t_concreto2.dxf" in texts, "The title block names the file"

    def test_beams(self, t_concreto2: Pavement, tmp_path: Path) -> None:
        for beam in detailings(t_concreto2):
            doc = read_dxf(export_beam_dxf(beam, tmp_path / f"{beam.beam_id}.dxf"))
            assert not doc.audit().has_errors, f"{beam.beam_id}: clean audit"
            texts = {
                entity.dxf.text
                for entity in doc.modelspace()
                if entity.dxftype() == "TEXT"
            }
            marks = {row.mark for row in build_schedule([beam])}
            assert marks <= texts, f"{beam.beam_id}: every mark of its schedule"
            layers = {entity.dxf.layer for entity in doc.modelspace()}
            assert layers <= set(LAYERS), f"{beam.beam_id}: only the table's layers"
