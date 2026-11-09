"""Write report and drawing files under a wait cursor, reporting write errors."""

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

from pavement_ui.presentation.dialogs.file_dialogs import ask_pdf_path
from pavement_ui.presentation.dialogs.messages import show_export_error
from pavement_ui.presentation.report.pdf_export import export_pdf
from pavement_ui.presentation.report.report_builder import PRINT_DPI, ReportBuilder
from pavement_ui.presentation.text.strings import dialogs as d

type WriteReport = Callable[[ReportBuilder], None]


def write_file(
    parent: QWidget,
    path: Path,
    write: Callable[[Path], None],
    error_title: str = d.EXPORT_PDF_TITLE,
    error_text: str = d.EXPORT_FAILED,
) -> bool:
    """Run write(path) under a wait cursor; show the error box if it raises OSError

    Returns:
        Whether the file was written.
    """
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        write(path)
    except OSError as error:
        QApplication.restoreOverrideCursor()
        show_export_error(
            parent, d.FILE_WRITE_FAILED.format(detail=error), error_title, error_text
        )
        return False
    QApplication.restoreOverrideCursor()
    return True


def export_report(
    parent: QWidget, write: WriteReport, suggested_name: str, title: str
) -> None:
    """Ask where to save, rebuild the report with 300 dpi figures and write the PDF

    Args:
        write: Appends the report to a builder.
        suggested_name: File name proposed in the dialog.
        title: Title stored in the PDF.
    """
    path = ask_pdf_path(parent, suggested_name)
    if path is None:
        return

    def write_pdf(target: Path) -> None:
        builder = ReportBuilder(PRINT_DPI)
        write(builder)
        export_pdf(builder.document(), target, title)

    write_file(parent, path, write_pdf)
