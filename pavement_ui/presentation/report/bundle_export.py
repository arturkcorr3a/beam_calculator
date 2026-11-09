"""Write every report and detailing sheet of a design into one ZIP file."""

import tempfile
import zipfile
from pathlib import Path

from PySide6.QtWidgets import QWidget

from pavement_ui.core.ports import DrawingExporter
from pavement_ui.core.results.outcomes import DesignSuccess
from pavement_ui.presentation.dialogs.file_dialogs import ask_folder
from pavement_ui.presentation.dialogs.messages import (
    confirm_overwrite,
    show_bundle_done,
)
from pavement_ui.presentation.report.beam_report import write_beam_report
from pavement_ui.presentation.report.drawing_pdf import export_drawing_pdf
from pavement_ui.presentation.report.pavement_report import write_pavement_report
from pavement_ui.presentation.report.pdf_export import export_pdf
from pavement_ui.presentation.report.report_builder import PRINT_DPI, ReportBuilder
from pavement_ui.presentation.report.report_exporter import write_file
from pavement_ui.presentation.report.slab_report import write_slab_report
from pavement_ui.presentation.text.strings import dialogs as d
from pavement_ui.presentation.text.strings import report as rs
from pavement_ui.presentation.text.strings import results as s

_REPORTS = Path("relatorios")
_SHEETS = Path("detalhamento")


def _write_reports(folder: Path, success: DesignSuccess, name: str) -> int:
    """Write the pavement, beam and slab reports; return how many were written"""
    (folder / _REPORTS / "vigas").mkdir(parents=True)
    (folder / _REPORTS / "lajes").mkdir(parents=True)
    builder = ReportBuilder(PRINT_DPI)
    write_pavement_report(builder, success, name)
    title = rs.PDF_TITLE_PAVEMENT.format(name=name)
    export_pdf(builder.document(), folder / _REPORTS / "pavimento.pdf", title)
    for beam in success.beams:
        builder = ReportBuilder(PRINT_DPI)
        write_beam_report(builder, beam, success)
        path = folder / _REPORTS / "vigas" / f"{beam.beam_id}.pdf"
        export_pdf(
            builder.document(), path, rs.BEAM_REPORT_TITLE.format(id=beam.beam_id)
        )
    for slab in success.slabs:
        builder = ReportBuilder(PRINT_DPI)
        write_slab_report(builder, slab)
        path = folder / _REPORTS / "lajes" / f"{slab.slab_id}.pdf"
        export_pdf(
            builder.document(), path, rs.SLAB_REPORT_TITLE.format(id=slab.slab_id)
        )
    return 1 + len(success.beams) + len(success.slabs)


def _write_sheets(
    folder: Path, success: DesignSuccess, exporter: DrawingExporter
) -> int:
    """Write each detailed beam's sheet as PDF and DXF; return how many sheets"""
    (folder / _SHEETS).mkdir()
    count = 0
    for beam in success.beams:
        if beam.sheet is None:
            continue
        stem = folder / _SHEETS / beam.beam_id
        title = s.DRAWING_PDF_TITLE.format(id=beam.beam_id)
        export_drawing_pdf(beam.sheet, stem.with_suffix(".pdf"), title)
        exporter.write_dxf(beam.sheet, stem.with_suffix(".dxf"))
        count += 1
    return count


def _zip_folder(folder: Path, target: Path) -> None:
    """Zip every file under folder into target, with paths relative to folder"""
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(folder).as_posix())


def export_bundle(
    parent: QWidget, success: DesignSuccess, name: str, exporter: DrawingExporter
) -> None:
    """Ask for a folder and write <name>_resultados.zip with every report and sheet

    The ZIP holds relatorios/pavimento.pdf, relatorios/vigas/<id>.pdf,
    relatorios/lajes/<id>.pdf, and detalhamento/<id>.pdf and .dxf for each
    detailed beam. The files are written to a temporary folder, then zipped.

    Args:
        name: Project name, for the file and the titles.
    """
    folder = ask_folder(parent)
    if folder is None:
        return
    target = folder / d.BUNDLE_FILE_NAME.format(name=name)
    if target.exists() and not confirm_overwrite(parent, str(target)):
        return
    counts: list[int] = []

    def write(path: Path) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            staging = Path(temporary)
            counts.append(_write_reports(staging, success, name))
            counts.append(_write_sheets(staging, success, exporter))
            _zip_folder(staging, path)

    if write_file(parent, target, write, d.BUNDLE_TITLE, d.BUNDLE_FAILED):
        show_bundle_done(parent, str(target), counts[0], counts[1])
