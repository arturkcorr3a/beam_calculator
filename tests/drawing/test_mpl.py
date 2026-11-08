"""Tests for the screen figures and the hover tooltip (spec §9, §11 test_mpl)."""

# matplotlib leaves **kwargs unannotated, so draw and process are partially unknown
# pyright: reportUnknownMemberType=false

from collections.abc import Iterator

import matplotlib.pyplot as plt
import pytest
from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseEvent
from matplotlib.figure import Figure

from src.detailing.detailing_beam import DetailingBeam
from src.drawing.api import beam_figure, pavement_figure
from src.drawing.render_mpl import TOOLTIPS, HoverTooltip
from src.pavement_elements.pavement import Pavement
from tests.drawing.helpers import detailings


@pytest.fixture(autouse=True)
def _close_figures() -> Iterator[None]:
    """Close the figures each test opens"""
    yield
    plt.close("all")


def _move(figure: Figure, ax: Axes, x: float, y: float) -> None:
    """Send a mouse move over a point of the drawing (cm)"""
    px, py = ax.transData.transform((x, y))
    event = MouseEvent("motion_notify_event", figure.canvas, round(px), round(py))
    figure.canvas.callbacks.process("motion_notify_event", event)


def _ready(detailing: DetailingBeam) -> tuple[Figure, Axes, HoverTooltip]:
    """Return a beam's figure, drawn once so its transforms are final, and its tooltip"""
    figure = beam_figure(detailing)
    figure.canvas.draw()
    return figure, figure.axes[0], TOOLTIPS[figure]


class TestTooltip:
    """Hovering a bar shows its data."""

    def test_hover_bar(self, v5: DetailingBeam) -> None:
        figure, ax, tooltip = _ready(v5)
        _move(figure, ax, 645.0, 3.5)  # middle of N12 on the elevation
        assert tooltip.box.get_visible(), "The tooltip shows over a bar"
        assert tooltip.highlight.get_visible(), "The bar is highlighted"
        assert tooltip.title.get_text() == "N12 · 2 φ10 CA-50", "The bar's title"
        assert "traspasse 30 com N10 e N13" in tooltip.body.get_text(), "Its laps"

    def test_hover_clamp(self, v5: DetailingBeam) -> None:
        figure, ax, tooltip = _ready(v5)
        points = next(p for meta, p in tooltip.items if meta.title.startswith("N14"))
        y = points[0][1]
        _move(figure, ax, 1190.0, y)
        assert tooltip.box.get_visible(), "The tooltip shows over a clamp"
        assert tooltip.title.get_text().startswith("N14 · 2 φ6,3"), "The clamp's title"

    def test_away_hides(self, v5: DetailingBeam) -> None:
        figure, ax, tooltip = _ready(v5)
        _move(figure, ax, 645.0, 3.5)
        _move(figure, ax, 645.0, 300.0)  # empty space above the beam
        assert not tooltip.box.get_visible(), "No bar, no tooltip"
        assert not tooltip.highlight.get_visible(), "No bar, no highlight"

    def test_redraw_only_on_change(
        self, v5: DetailingBeam, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        figure, ax, _ = _ready(v5)
        redraws: list[bool] = []

        def count() -> None:
            redraws.append(True)

        monkeypatch.setattr(figure.canvas, "draw_idle", count)
        _move(figure, ax, 645.0, 300.0)
        _move(figure, ax, 600.0, 300.0)
        assert redraws == [], "Moving over empty space does not redraw"
        _move(figure, ax, 645.0, 3.5)
        assert redraws == [True], "Reaching a bar redraws once"

    def test_bar_rows_hover(self, v5: DetailingBeam) -> None:
        figure, ax, tooltip = _ready(v5)
        n12 = [
            points for meta, points in tooltip.items if meta.title.startswith("N12 ")
        ]
        assert len(n12) == 2, "N12 on the elevation and on its row"
        row_y = n12[1][0][1]
        _move(figure, ax, 645.0, row_y)
        assert tooltip.title.get_text().startswith("N12 "), (
            "The row copy has the tooltip too"
        )


class TestFigures:
    """Figures open without errors and show coordinates with a comma."""

    def test_format_coord(self, v5: DetailingBeam) -> None:
        ax = beam_figure(v5).axes[0]
        assert ax.format_coord(12.34, -5.0) == "x = 12,3 cm   y = -5,0 cm", "Comma"

    @pytest.mark.slow
    def test_t_concreto2(self, t_concreto2: Pavement) -> None:
        for beam in detailings(t_concreto2):
            figure = beam_figure(beam)
            figure.canvas.draw()
            plt.close(figure)
        figure = pavement_figure(t_concreto2, pavement_name="t_concreto2")
        figure.canvas.draw()
        assert TOOLTIPS[figure].items, "The pavement figure has hover targets"
