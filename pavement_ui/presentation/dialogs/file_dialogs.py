"""Choose project files to open or save (*.yaml / *.yml) and report files to export (*.pdf)."""

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QWidget

from pavement_ui.presentation.text.strings import dialogs as s


def ask_open_path(parent: QWidget | None) -> Path | None:
    """Ask for a project file to open; None if cancelled"""
    name, _ = QFileDialog.getOpenFileName(parent, s.OPEN_FILE_TITLE, "", s.FILE_FILTER)
    return Path(name) if name else None


def ask_save_path(parent: QWidget | None, current: Path | None) -> Path | None:
    """Ask where to save; ".yaml" is added when no extension is given. None if cancelled"""
    start = str(current) if current is not None else ""
    name, _ = QFileDialog.getSaveFileName(
        parent, s.SAVE_FILE_TITLE, start, s.FILE_FILTER
    )
    if not name:
        return None
    path = Path(name)
    return path if path.suffix else path.with_suffix(s.FILE_EXTENSION)


def ask_pdf_path(parent: QWidget | None, suggested_name: str) -> Path | None:
    """Ask where to export a report; ".pdf" is added when missing. None if cancelled"""
    name, _ = QFileDialog.getSaveFileName(
        parent, s.EXPORT_PDF_TITLE, suggested_name, s.PDF_FILTER
    )
    if not name:
        return None
    path = Path(name)
    return (
        path
        if path.suffix.lower() == s.PDF_EXTENSION
        else path.with_name(path.name + s.PDF_EXTENSION)
    )
