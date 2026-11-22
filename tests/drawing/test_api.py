"""Tests for src/drawing/api.py."""

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt
import pytest

from src.detailing.detailing_beam import DetailingBeam
from src.drawing.api import (
    beam_figure,
    export_beam_dxf,
    pavement_figures,
    save_pavement,
    show_beam,
)
from src.errors import DrawingError
from tests.drawing.helpers import fake_pavement, read_dxf


@pytest.fixture(autouse=True)
def _close_figures() -> Iterator[None]:
    """Close the figures each test opens"""
    yield
    plt.close("all")


def _unmarked(beam: DetailingBeam) -> DetailingBeam:
    """Return the beam as beam.detail() leaves it: no marks"""
    return replace(beam, bars=[replace(bar, mark=None) for bar in beam.bars])


class TestPreconditions:
    """Drawing needs the marks given by pavement.resolve()."""

    def test_beam_without_marks(self, v5: DetailingBeam) -> None:
        with pytest.raises(DrawingError, match="rode pavement.resolve"):
            beam_figure(_unmarked(v5))

    def test_dxf_without_marks(self, v5: DetailingBeam, tmp_path: Path) -> None:
        with pytest.raises(DrawingError):
            export_beam_dxf(_unmarked(v5), tmp_path / "v5.dxf")
        assert not (tmp_path / "v5.dxf").exists(), "Nothing is written"

    def test_pavement_beam_not_detailed(self, v5: DetailingBeam) -> None:
        pavement = fake_pavement(v5)
        pavement.beams["V5"].detailing = None
        with pytest.raises(DrawingError, match="V5"):
            pavement_figures(pavement)

    def test_is_a_value_error(self) -> None:
        assert issubclass(DrawingError, ValueError), "Spec §10"


class TestOutputs:
    """Figures and files of a beam and a pavement."""

    def test_beam_figure(self, v5: DetailingBeam) -> None:
        figure = beam_figure(v5)
        assert figure.axes, "The figure has the drawing's axes"

    @pytest.mark.filterwarnings("ignore:FigureCanvasAgg is non-interactive")
    def test_show_beam_returns_figure(self, v5: DetailingBeam) -> None:
        figure = show_beam(v5, block=False)
        assert figure.axes, "show_beam returns its figure"

    def test_export_beam_dxf(self, v5: DetailingBeam, tmp_path: Path) -> None:
        path = export_beam_dxf(v5, str(tmp_path / "V5.dxf"))
        doc = read_dxf(path)
        assert not doc.audit().has_errors, "Clean audit"
        texts = {
            entity.dxf.text for entity in doc.modelspace() if entity.dxftype() == "TEXT"
        }
        assert {"V5", "P10", "411", "N9 c/17"} <= texts, "Title, pillars, dimensions"

    def test_export_dxf_has_sheet(self, v5: DetailingBeam, tmp_path: Path) -> None:
        doc = read_dxf(export_beam_dxf(v5, tmp_path / "V5.dxf"))
        layers = {entity.dxf.layer for entity in doc.modelspace()}
        assert {"FOLHA-QUADRO", "SELO-GROSSO", "SELO-FINO", "SELO-LOGO"} <= layers, (
            "Frame, block lines and the logo's rectangle"
        )
        texts = {
            entity.dxf.text for entity in doc.modelspace() if entity.dxftype() == "TEXT"
        }
        assert "NOTAS GERAIS" in texts and "01/01" in texts, "Notes and sheet number"

    def test_sheet_numbers(self, v5: DetailingBeam, tmp_path: Path) -> None:
        pavement = fake_pavement(v5, replace(v5, beam_id="V6"))
        save_pavement(pavement, tmp_path)
        texts = {
            entity.dxf.text
            for name in ("V5", "V6")
            for entity in read_dxf(tmp_path / f"{name}.dxf").modelspace()
            if entity.dxftype() == "TEXT"
        }
        assert {"01/02", "02/02"} <= texts, "Numbered in pavement order"

    def test_save_pavement(self, v5: DetailingBeam, tmp_path: Path) -> None:
        folder = tmp_path / "drawing"
        paths = save_pavement(fake_pavement(v5), folder)
        assert sorted(path.name for path in paths) == [
            "V5.dxf",
            "V5.pdf",
            "V5.png",
            "pavement.pdf",
        ], "DXF, PNG and PDF per beam; one PDF with every sheet"
        assert all(path.parent == folder and path.stat().st_size > 0 for path in paths)
        assert not plt.get_fignums(), "Every saved figure is closed"
