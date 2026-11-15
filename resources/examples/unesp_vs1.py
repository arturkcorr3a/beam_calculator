"""Beam VS1 of Bastos (UNESP Bauru), item 19: two spans, end pillars as elastic restraints.

Reference: BASTOS, P. S. S. Vigas de Concreto Armado. UNESP, Bauru/SP, item 19
(p. 74–97). Run from anywhere::

    python resources/examples/unesp_vs1.py [--output DIR] [--show]

It dimensions and details the beam with the engine and writes, to
``results/<mmm-dd>/unesp_vs1/`` (or ``--output``):

* ``VS1.dxf``, ``VS1.png`` and ``VS1.pdf``: the detailing sheet;
* ``VS1_detalhamento.txt``: the detailing report (bars, splices, stirrups);
* ``VS1_relatorio.pdf``: the design report the interface exports (needs PySide6).

Differences from the book, none of them in the model:

* the book fixes d, the cover and the bars by hand; the engine chooses them;
* the book redistributes the negative moment at P2 (delta = 0.85); the engine does not;
* the book's pillar spring is 6EI/l with l = 300 cm (each 300 cm stretch pinned at both
  ends); the engine's is 12EI/h with the stretches pinned at mid-height, so
  ``ceiling_height`` is 6.0 m below to give the same 6EI/300 (about 6,996 and
  27,540 kN.m/rad for P1 and P3);
* the engine gives P2 a rotational spring too (27,537 kN.m/rad), while the book takes it
  as a pin because b_int = 30 cm < l_e/4 = 75 cm. That changes M(P2) from -135.4 to
  -136.6 kN.m (0.9 %), M(P1) from -10.4 to -10.3 and M(P3) from -28.4 to -28.7.
"""

import argparse
import os
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt  # noqa: E402

from src.calculators.isolated_beam import (  # noqa: E402
    CustomLoad,
    IsolatedPillar,
    OwnWeightLoad,
    build_isolated_beam,
    detail_isolated_beam,
)
from src.config import APP_CONFIG  # noqa: E402
from src.config_options import Aggregate, ExposureClass  # noqa: E402
from src.detailing.detailing_report import build_report  # noqa: E402
from src.drawing.api import beam_figure, export_beam_dxf  # noqa: E402
from src.properties.concrete import Concrete  # noqa: E402

NAME = "unesp_vs1"
BEAM_ID = "VS1"

SPANS = [719.0, 713.5]  # cm, effective spans (axis to axis of the pillars)
WIDTH = 19.0  # cm
HEIGHT = 60.0  # cm
# Width along the beam axis, depth across it (P1 19/19, P2 and P3 19/30 in the book)
PILLARS = [
    IsolatedPillar(19.0, 19.0),
    IsolatedPillar(30.0, 19.0),
    IsolatedPillar(30.0, 19.0),
]

# Slab: 5.45 kN/m² total, of which 2.00 variable, over 5.23 m, half on each beam
SLAB_SPAN = 5.23  # m
SLAB_PERMANENT = (5.45 - 2.00) * SLAB_SPAN / 2  # kN/m
SLAB_VARIABLE = 2.00 * SLAB_SPAN / 2  # kN/m
WALL = 2.3 * 2.40  # kN/m, 2.3 kN/m² × 2.40 m (hollow ceramic block, 23 cm)
PSI_2 = 0.3  # NBR 6118:2014 Table 11.2, buildings


def configure() -> None:
    """Set the materials and the pillar height of the example"""
    APP_CONFIG.pavement_concrete = Concrete.C30
    APP_CONFIG.aggregate = Aggregate.BASALT
    APP_CONFIG.exposure_class = (
        ExposureClass.WEAK
    )  # CAA I, wk,max = 0.4 mm as in the book
    APP_CONFIG.ceiling_height = 6.0  # m, see the module docstring


def output_folder(argument: str | None) -> Path:
    """Return the folder for the files, created if missing"""
    if argument is not None:
        folder = Path(argument)
    else:
        day = date.today().strftime("%b-%d").lower()
        folder = PROJECT_ROOT / "results" / day / NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def write_drawings(detailing: object, folder: Path, show: bool) -> list[Path]:
    """Write the sheet as DXF, PNG and PDF, and optionally show it"""
    from src.detailing.detailing_beam import DetailingBeam

    assert isinstance(detailing, DetailingBeam)
    paths = [export_beam_dxf(detailing, folder / f"{BEAM_ID}.dxf", pavement_name=NAME)]
    figure = beam_figure(detailing, pavement_name=NAME)
    for suffix in (".png", ".pdf"):
        path = folder / f"{BEAM_ID}{suffix}"
        figure.savefig(path, dpi=200)
        paths.append(path)
    if show:
        plt.show()
    plt.close(figure)
    return paths


def write_design_report(
    beam: object, pillars: object, detailing: object, folder: Path
) -> Path | None:
    """Write the interface's design report as PDF; None when PySide6 is missing"""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("PySide6 not installed: the design report PDF was skipped.")
        return None
    from pavement_ui.core.engine.readers.beam_reader import read_beam
    from pavement_ui.core.engine.readers.materials_reader import read_materials
    from pavement_ui.core.engine.readers.quantities_reader import read_beam_quantity
    from pavement_ui.presentation.report.beam_report import write_beam_report
    from pavement_ui.presentation.report.pdf_export import export_pdf
    from pavement_ui.presentation.report.report_builder import PRINT_DPI, ReportBuilder

    application = QApplication.instance() or QApplication(sys.argv[:1])
    result = read_beam(beam, pillars)  # type: ignore[arg-type]
    builder = ReportBuilder(PRINT_DPI)
    write_beam_report(
        builder,
        result,
        read_materials(),
        read_beam_quantity(detailing),  # type: ignore[arg-type]
    )
    path = folder / f"{BEAM_ID}_relatorio.pdf"
    export_pdf(builder.document(), path, f"Relatório da viga {BEAM_ID}")
    del application
    return path


def main(argv: Sequence[str] | None = None) -> None:
    """Dimension and detail VS1, then write the drawings and the reports"""
    parser = argparse.ArgumentParser(description="Run the UNESP VS1 beam example.")
    parser.add_argument(
        "--output", help="Folder for the files (default: results/<day>/unesp_vs1)."
    )
    parser.add_argument(
        "--show", action="store_true", help="Open the detailing sheet in a window."
    )
    args = parser.parse_args(argv)
    if not args.show:
        plt.switch_backend("Agg")

    configure()
    loads = [
        OwnWeightLoad(),
        CustomLoad("parede", WALL),
        CustomLoad("laje (permanente)", SLAB_PERMANENT),
        CustomLoad("laje (sobrecarga)", SLAB_VARIABLE, variable=True, psi_2=PSI_2),
    ]
    beam, pillars = build_isolated_beam(SPANS, WIDTH, HEIGHT, PILLARS, loads, BEAM_ID)
    beam.dimension(pillars)
    detailing = detail_isolated_beam(beam)

    folder = output_folder(args.output)
    report = folder / f"{BEAM_ID}_detalhamento.txt"
    report.write_text(build_report(detailing), encoding="utf-8")
    files = [report, *write_drawings(detailing, folder, args.show)]
    design_report = write_design_report(beam, pillars, detailing, folder)
    if design_report is not None:
        files.append(design_report)
    print(f"[{NAME}] {len(files)} files in {folder}")
    for path in files:
        print(f"  {path.name}")


if __name__ == "__main__":
    main()
