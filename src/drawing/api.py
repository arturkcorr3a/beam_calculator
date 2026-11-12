"""Public entry points of the drawings: figures on screen, and DXF, PNG and PDF files"""

# matplotlib leaves **kwargs unannotated, so show and savefig are partially unknown
# pyright: reportUnknownMemberType=false

from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from src.detailing.detailing_beam import DetailingBeam
from src.drawing.config import DEFAULT_CONFIG, DrawingConfig
from src.drawing.layout import build_beam_drawing, build_pavement_drawing
from src.drawing.render_dxf import write_dxf
from src.drawing.render_mpl import make_figure
from src.drawing.sheet_info import read_sheet_info
from src.pavement_elements.pavement import Pavement

MISSING_MARKS = "Detalhamento sem posições: rode pavement.resolve() antes de desenhar."
PNG_DPI = 200


class DrawingError(ValueError):
    """The beam or pavement cannot be drawn as it is"""


def check_detailing(detailing: DetailingBeam) -> None:
    """Check that every bar, clamp and stirrup of a beam has its mark

    Raises:
        DrawingError: If any mark is missing, as after ``beam.detail()`` without ``pavement.resolve()``.
    """
    items = [*detailing.bars, *detailing.clamps, *detailing.stirrups]
    if any(item.mark is None for item in items):
        raise DrawingError(f"{detailing.beam_id}: {MISSING_MARKS}")


def pavement_detailings(pavement: Pavement) -> list[DetailingBeam]:
    """Return the detailing of every beam, in pavement order, after checking them

    Raises:
        DrawingError: If the pavement has no beams, or a beam is not detailed or has items without marks.
    """
    if not pavement.beams:
        raise DrawingError("O pavimento não tem vigas para desenhar.")
    detailings: list[DetailingBeam] = []
    for beam in pavement.beams.values():
        if beam.detailing is None:
            raise DrawingError(f"{beam.id}: {MISSING_MARKS}")
        check_detailing(beam.detailing)
        detailings.append(beam.detailing)
    return detailings


def beam_figure(
    detailing: DetailingBeam,
    config: DrawingConfig | None = None,
    *,
    pavement_name: str | None = None,
) -> Figure:
    """Return the figure of one beam's sheet

    Args:
        pavement_name: Name shown in the title block.

    Raises:
        DrawingError: If the detailing has items without marks.
    """
    config = config or DEFAULT_CONFIG
    check_detailing(detailing)
    drawing = build_beam_drawing(
        detailing, config, sheet=read_sheet_info(pavement_name)
    )
    figure = make_figure(drawing, config)
    _set_window_title(figure, f"Viga {detailing.beam_id}")
    return figure


def pavement_figure(
    pavement: Pavement,
    config: DrawingConfig | None = None,
    *,
    pavement_name: str | None = None,
) -> Figure:
    """Return the figure of a pavement's sheet: every beam, stacked, then the closing blocks

    Args:
        pavement_name: Name shown in the title block.

    Raises:
        DrawingError: If a beam is not detailed or has items without marks.
    """
    config = config or DEFAULT_CONFIG
    pavement_detailings(pavement)
    drawing = build_pavement_drawing(
        pavement, config, sheet=read_sheet_info(pavement_name)
    )
    figure = make_figure(drawing, config)
    _set_window_title(figure, "Vigas do pavimento")
    return figure


def show_beam(
    detailing: DetailingBeam,
    config: DrawingConfig | None = None,
    *,
    block: bool = True,
    pavement_name: str | None = None,
) -> Figure:
    """Show one beam's sheet in a window and return its figure

    Raises:
        DrawingError: If the detailing has items without marks.
    """
    figure = beam_figure(detailing, config, pavement_name=pavement_name)
    plt.show(block=block)
    return figure


def show_pavement(
    pavement: Pavement,
    config: DrawingConfig | None = None,
    *,
    block: bool = True,
    pavement_name: str | None = None,
) -> Figure:
    """Show a pavement's sheet in a window and return its figure

    Raises:
        DrawingError: If a beam is not detailed or has items without marks.
    """
    figure = pavement_figure(pavement, config, pavement_name=pavement_name)
    plt.show(block=block)
    return figure


def export_beam_dxf(
    detailing: DetailingBeam,
    path: str | Path,
    config: DrawingConfig | None = None,
    *,
    pavement_name: str | None = None,
) -> Path:
    """Write one beam's sheet, with its summary, legend and title block, to a DXF file

    Returns:
        The path written.

    Raises:
        DrawingError: If the detailing has items without marks.
    """
    config = config or DEFAULT_CONFIG
    path = Path(path)
    check_detailing(detailing)
    sheet = replace(read_sheet_info(pavement_name), file_name=path.name)
    return write_dxf(build_beam_drawing(detailing, config, sheet=sheet), path, config)


def export_pavement_dxf(
    pavement: Pavement,
    path: str | Path,
    config: DrawingConfig | None = None,
    *,
    pavement_name: str | None = None,
) -> Path:
    """Write a pavement's sheet to a DXF file

    Returns:
        The path written.

    Raises:
        DrawingError: If a beam is not detailed or has items without marks.
    """
    config = config or DEFAULT_CONFIG
    path = Path(path)
    pavement_detailings(pavement)
    sheet = replace(read_sheet_info(pavement_name), file_name=path.name)
    return write_dxf(
        build_pavement_drawing(pavement, config, sheet=sheet), path, config
    )


def save_pavement(
    pavement: Pavement,
    folder: str | Path,
    config: DrawingConfig | None = None,
    *,
    pavement_name: str | None = None,
) -> list[Path]:
    """Write every drawing of a pavement to a folder and return the files

    Each beam gets a DXF, a PNG and a PDF named after it (V1.dxf, …), and the whole pavement a ``pavement.dxf`` and a ``pavement.pdf``. Figures are closed once saved.

    Args:
        pavement_name: Name shown in the title blocks.

    Raises:
        DrawingError: If a beam is not detailed or has items without marks.
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for detailing in pavement_detailings(pavement):
        stem = folder / detailing.beam_id
        paths.append(
            export_beam_dxf(
                detailing, stem.with_suffix(".dxf"), config, pavement_name=pavement_name
            )
        )
        figure = beam_figure(detailing, config, pavement_name=pavement_name)
        paths += _save_figure(figure, stem, (".png", ".pdf"))
    paths.append(
        export_pavement_dxf(
            pavement, folder / "pavement.dxf", config, pavement_name=pavement_name
        )
    )
    figure = pavement_figure(pavement, config, pavement_name=pavement_name)
    paths += _save_figure(figure, folder / "pavement", (".pdf",))
    return paths


def _save_figure(figure: Figure, stem: Path, suffixes: tuple[str, ...]) -> list[Path]:
    """Save a figure in some formats next to each other, close it, and return the files"""
    paths = [stem.with_suffix(suffix) for suffix in suffixes]
    for path in paths:
        figure.savefig(path, dpi=PNG_DPI)
    plt.close(figure)
    return paths


def _set_window_title(figure: Figure, title: str) -> None:
    """Name the figure's window, when it has one"""
    manager = figure.canvas.manager
    if manager is not None:
        manager.set_window_title(title)
