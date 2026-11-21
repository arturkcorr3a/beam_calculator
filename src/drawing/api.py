"""Public entry points of the drawings: figures on screen, and DXF, PNG and PDF files"""

# matplotlib leaves **kwargs unannotated, so show and savefig are partially unknown
# pyright: reportUnknownMemberType=false

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure

from src.detailing.detailing_beam import DetailingBeam
from src.drawing.config import DEFAULT_CONFIG, DrawingConfig
from src.drawing.layout import build_beam_drawing
from src.drawing.render_dxf import write_dxf
from src.drawing.render_mpl import make_figure
from src.drawing.sheet_info import read_sheet_info
from src.pavement_elements.pavement import Pavement

MISSING_MARKS = "Detalhamento sem posições: rode pavement.resolve() antes de desenhar."
PNG_DPI = 200


class DrawingError(ValueError):
    """The beam or pavement cannot be drawn as it is"""


def check_detailing(detailing: DetailingBeam) -> None:
    """Check that every bar, skin bar, clamp and stirrup of a beam has its mark

    Raises:
        DrawingError: If any mark is missing, as after ``beam.detail()`` without ``pavement.resolve()``.
    """
    items = [
        *detailing.bars,
        *detailing.skin_bars,
        *detailing.clamps,
        *detailing.stirrups,
    ]
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
    sheet_number: int = 1,
    sheet_total: int = 1,
) -> Figure:
    """Return the figure of one beam's sheet

    Args:
        pavement_name: Name shown in the title block as the project's.
        sheet_number: Number of the sheet among the exported ones, from 1.
        sheet_total: Number of sheets exported together.

    Raises:
        DrawingError: If the detailing has items without marks.
        SheetFitError: If a fixed sheet format does not hold the drawing.
    """
    config = config or DEFAULT_CONFIG
    check_detailing(detailing)
    drawing = build_beam_drawing(
        detailing,
        config,
        sheet=read_sheet_info(pavement_name, sheet_number, sheet_total),
    )
    figure = make_figure(drawing, config)
    _set_window_title(figure, f"Viga {detailing.beam_id}")
    return figure


def pavement_figures(
    pavement: Pavement,
    config: DrawingConfig | None = None,
    *,
    pavement_name: str | None = None,
) -> list[Figure]:
    """Return the figure of each beam's sheet, in pavement order, numbered n/total

    Raises:
        DrawingError: If a beam is not detailed or has items without marks.
    """
    detailings = pavement_detailings(pavement)
    return [
        beam_figure(
            detailing,
            config,
            pavement_name=pavement_name,
            sheet_number=number,
            sheet_total=len(detailings),
        )
        for number, detailing in enumerate(detailings, start=1)
    ]


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
) -> list[Figure]:
    """Show the sheet of every beam of a pavement, one window each, and return the figures

    Raises:
        DrawingError: If a beam is not detailed or has items without marks.
    """
    figures = pavement_figures(pavement, config, pavement_name=pavement_name)
    plt.show(block=block)
    return figures


def export_beam_dxf(
    detailing: DetailingBeam,
    path: str | Path,
    config: DrawingConfig | None = None,
    *,
    pavement_name: str | None = None,
    sheet_number: int = 1,
    sheet_total: int = 1,
) -> Path:
    """Write one beam's sheet, with its frame, notes and title block, to a DXF file

    Returns:
        The path written.

    Raises:
        DrawingError: If the detailing has items without marks.
        SheetFitError: If a fixed sheet format does not hold the drawing.
    """
    config = config or DEFAULT_CONFIG
    path = Path(path)
    check_detailing(detailing)
    sheet = read_sheet_info(pavement_name, sheet_number, sheet_total)
    return write_dxf(build_beam_drawing(detailing, config, sheet=sheet), path, config)


def save_pavement(
    pavement: Pavement,
    folder: str | Path,
    config: DrawingConfig | None = None,
    *,
    pavement_name: str | None = None,
) -> list[Path]:
    """Write every drawing of a pavement to a folder and return the files

    Each beam gets a DXF, a PNG and a PDF named after it (V1.dxf, …), numbered n/total in pavement order, and ``pavement.pdf`` holds all the sheets, one per page. Figures are closed once saved.

    Args:
        pavement_name: Name shown in the title blocks.

    Raises:
        DrawingError: If a beam is not detailed or has items without marks.
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    detailings = pavement_detailings(pavement)
    paths: list[Path] = []
    figures: list[Figure] = []
    for number, detailing in enumerate(detailings, start=1):
        stem = folder / detailing.beam_id
        paths.append(
            export_beam_dxf(
                detailing,
                stem.with_suffix(".dxf"),
                config,
                pavement_name=pavement_name,
                sheet_number=number,
                sheet_total=len(detailings),
            )
        )
        figure = beam_figure(
            detailing,
            config,
            pavement_name=pavement_name,
            sheet_number=number,
            sheet_total=len(detailings),
        )
        paths += _save_figure(figure, stem, (".png", ".pdf"), close=False)
        figures.append(figure)
    all_sheets = folder / "pavement.pdf"
    with PdfPages(all_sheets) as pdf:
        for figure in figures:
            pdf.savefig(figure)
            plt.close(figure)
    return [*paths, all_sheets]


def _save_figure(
    figure: Figure, stem: Path, suffixes: tuple[str, ...], *, close: bool = True
) -> list[Path]:
    """Save a figure in some formats next to each other, optionally close it, and return the files"""
    paths = [stem.with_suffix(suffix) for suffix in suffixes]
    for path in paths:
        figure.savefig(path, dpi=PNG_DPI)
    if close:
        plt.close(figure)
    return paths


def _set_window_title(figure: Figure, title: str) -> None:
    """Name the figure's window, when it has one"""
    manager = figure.canvas.manager
    if manager is not None:
        manager.set_window_title(title)
