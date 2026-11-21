"""Choose project and isolated beam files to open or save (*.pavement.yaml / *.beam.yaml), examples to open, and report files to export (*.pdf)."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QWidget

from pavement_ui.presentation.text.strings import dialogs as s

# Shipped next to the executable in the packages; resources/examples/ in the repository
_PACKAGED_EXAMPLES = "exemplos"
_SOURCE_EXAMPLES = Path(__file__).parents[3] / "resources" / "examples"


def examples_dir() -> Path:
    """Folder of the example pavement and isolated beam files and their templates

    The packaged app (PyInstaller sets sys.frozen) has it next to its
    executable; resolve() follows the RPM's /usr/bin link to /opt.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / _PACKAGED_EXAMPLES
    return _SOURCE_EXAMPLES


def ask_open_path(parent: QWidget | None) -> Path | None:
    """Ask for a project file to open; None if cancelled"""
    name, _ = QFileDialog.getOpenFileName(parent, s.OPEN_FILE_TITLE, "", s.FILE_FILTER)
    return Path(name) if name else None


def ask_example_path(parent: QWidget | None) -> Path | None:
    """Ask for an example to open, starting in the examples folder; None if cancelled"""
    folder = examples_dir()
    start = str(folder) if folder.is_dir() else ""
    name, _ = QFileDialog.getOpenFileName(
        parent, s.OPEN_EXAMPLE_TITLE, start, s.FILE_FILTER
    )
    return Path(name) if name else None


def ask_save_path(parent: QWidget | None, current: Path | None) -> Path | None:
    """Ask where to save a pavement; the name always ends in ".pavement.yaml"

    A plain ".yaml" / ".yml" ending is replaced. None if cancelled.
    """
    return _ask_typed_save_path(
        parent,
        s.SAVE_FILE_TITLE,
        current,
        s.FILE_FILTER,
        s.FILE_EXTENSION,
        s.FILE_EXTENSIONS,
    )


def ask_beam_open_path(parent: QWidget | None) -> Path | None:
    """Ask for an isolated beam file to open; None if cancelled"""
    name, _ = QFileDialog.getOpenFileName(
        parent, s.OPEN_BEAM_TITLE, "", s.BEAM_FILE_FILTER
    )
    return Path(name) if name else None


def ask_beam_save_path(parent: QWidget | None, current: Path | None) -> Path | None:
    """Ask where to save an isolated beam; the name always ends in ".beam.yaml"

    A plain ".yaml" / ".yml" ending is replaced. None if cancelled.
    """
    return _ask_typed_save_path(
        parent,
        s.SAVE_BEAM_TITLE,
        current,
        s.BEAM_FILE_FILTER,
        s.BEAM_FILE_EXTENSION,
        s.BEAM_FILE_EXTENSIONS,
    )


def _ask_typed_save_path(
    parent: QWidget | None,
    title: str,
    current: Path | None,
    filter_: str,
    extension: str,
    extensions: tuple[str, ...],
) -> Path | None:
    """Ask where to save; the name always ends in one of extensions

    A plain ".yaml" / ".yml" ending is replaced by extension. None if cancelled.
    """
    start = str(current) if current is not None else ""
    name, _ = QFileDialog.getSaveFileName(parent, title, start, filter_)
    if not name:
        return None
    path = Path(name)
    if path.name.lower().endswith(extensions):
        return path
    if path.suffix.lower() in (".yaml", ".yml"):
        path = path.with_suffix("")
    return path.with_name(path.name + extension)


def _ask_export_path(
    parent: QWidget | None, title: str, suggested: str, filter_: str, extension: str
) -> Path | None:
    """Ask where to write a file; the extension is added when missing. None if cancelled"""
    name, _ = QFileDialog.getSaveFileName(parent, title, suggested, filter_)
    if not name:
        return None
    path = Path(name)
    if path.suffix.lower() == extension:
        return path
    return path.with_name(path.name + extension)


def ask_pdf_path(
    parent: QWidget | None, suggested_name: str, title: str = s.EXPORT_PDF_TITLE
) -> Path | None:
    """Ask where to export a PDF; ".pdf" is added when missing. None if cancelled"""
    return _ask_export_path(
        parent, title, suggested_name, s.PDF_FILTER, s.PDF_EXTENSION
    )


def ask_dxf_path(parent: QWidget | None, suggested_name: str) -> Path | None:
    """Ask where to export a DXF; ".dxf" is added when missing. None if cancelled"""
    return _ask_export_path(
        parent, s.EXPORT_DXF_TITLE, suggested_name, s.DXF_FILTER, s.DXF_EXTENSION
    )


def ask_folder(parent: QWidget | None) -> Path | None:
    """Ask for the folder of the results bundle; None if cancelled"""
    name = QFileDialog.getExistingDirectory(parent, s.BUNDLE_FOLDER_TITLE)
    return Path(name) if name else None
