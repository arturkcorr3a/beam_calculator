"""The only factory of message boxes.

Engine texts are translated here; callers pass the original messages.
"""

from collections.abc import Sequence

from PySide6.QtWidgets import QMessageBox, QWidget

from pavement_ui.core.errors import PersistenceError
from pavement_ui.core.model.element_kind import ElementKind
from pavement_ui.core.results.outcomes import UnexpectedFailure
from pavement_ui.presentation.formatting.numbers import fmt_length_cm
from pavement_ui.presentation.text.error_translation import file_error_text, translate
from pavement_ui.presentation.text.strings import dialogs as s
from pavement_ui.version import app_version

_Icon = QMessageBox.Icon
_Role = QMessageBox.ButtonRole

_INCLUSION_TEXTS: dict[ElementKind, tuple[str, str]] = {
    ElementKind.PILLAR: (s.INCLUDE_PILLAR_TITLE, s.PILLAR_NOT_CREATED),
    ElementKind.BEAM: (s.INCLUDE_BEAM_TITLE, s.BEAM_NOT_CREATED),
    ElementKind.SLAB: (s.INCLUDE_SLAB_TITLE, s.SLAB_NOT_CREATED),
}


def _box(
    parent: QWidget | None, icon: _Icon, title: str, text: str, detail: str = ""
) -> QMessageBox:
    """Build a standard box: bold main text, plain detail below."""
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(f"<b>{text}</b>")
    if detail:
        box.setInformativeText(detail)
    return box


def _confirm(
    parent: QWidget | None,
    icon: _Icon,
    title: str,
    text: str,
    detail: str,
    accept: str,
    destructive: bool,
) -> bool:
    """Ask with Cancel as the default; True if the accept button was chosen."""
    box = _box(parent, icon, title, text, detail)
    role = _Role.DestructiveRole if destructive else _Role.AcceptRole
    accept_button = box.addButton(accept, role)
    cancel_button = box.addButton(s.CANCEL, _Role.RejectRole)
    box.setDefaultButton(cancel_button)
    box.exec()
    return box.clickedButton() is accept_button


def show_inclusion_error(
    parent: QWidget | None, kind: ElementKind, message: str
) -> None:
    """The engine refused a new element"""
    title, text = _INCLUSION_TEXTS[kind]
    _box(parent, _Icon.Critical, title, text, translate(message)).exec()


def show_validation_error(parent: QWidget | None, message: str) -> None:
    _box(
        parent,
        _Icon.Critical,
        s.VALIDATE_TITLE,
        s.STRUCTURE_INVALID,
        translate(message),
    ).exec()


def show_validation_ok(parent: QWidget | None) -> None:
    _box(
        parent,
        _Icon.Information,
        s.VALIDATE_TITLE,
        s.STRUCTURE_VALID,
        s.STRUCTURE_VALID_DETAIL,
    ).exec()


def show_design_rule_error(parent: QWidget | None, message: str) -> None:
    _box(
        parent, _Icon.Critical, s.DESIGN_TITLE, s.DESIGN_INTERRUPTED, translate(message)
    ).exec()


def show_budget_error(parent: QWidget | None, message: str) -> None:
    """The engine refused the budget, e.g. a diameter without a SINAPI price"""
    _box(
        parent, _Icon.Critical, s.BUDGET_TITLE, s.BUDGET_FAILED, translate(message)
    ).exec()


def show_design_unexpected(parent: QWidget | None, failure: UnexpectedFailure) -> None:
    """An unexpected error; the traceback goes to the expandable details"""
    box = _box(
        parent, _Icon.Critical, s.DESIGN_TITLE, s.DESIGN_UNEXPECTED, failure.message
    )
    box.setDetailedText(failure.details)
    box.exec()


def confirm_clear(parent: QWidget | None) -> bool:
    return _confirm(
        parent,
        _Icon.Question,
        s.CLEAR_TITLE,
        s.CLEAR_QUESTION,
        s.CLEAR_DETAIL,
        s.CLEAR,
        True,
    )


def confirm_remove_pillar(
    parent: QWidget | None, pillar_id: str, dependents: Sequence[str]
) -> bool:
    """Ask before removing a pillar together with the elements that reference it"""
    return _confirm(
        parent,
        _Icon.Warning,
        s.REMOVE_PILLAR_TITLE,
        s.REMOVE_PILLAR_QUESTION.format(pillar=pillar_id),
        s.REMOVE_PILLAR_DETAIL.format(ids=", ".join(dependents)),
        s.REMOVE,
        True,
    )


def confirm_new(parent: QWidget | None) -> bool:
    return _confirm(
        parent, _Icon.Question, s.NEW_TITLE, s.NEW_QUESTION, s.NEW_DETAIL, s.NEW, False
    )


def confirm_save_invalid(parent: QWidget | None, message: str) -> bool:
    """Ask before saving a structure the engine considers invalid"""
    detail = s.SAVE_INVALID_DETAIL.format(error=translate(message))
    return _confirm(
        parent,
        _Icon.Warning,
        s.SAVE_FILE_TITLE,
        s.SAVE_INVALID_QUESTION,
        detail,
        s.SAVE,
        False,
    )


def show_file_error(
    parent: QWidget | None, error: PersistenceError, opening: bool
) -> None:
    title, text = (
        (s.OPEN_FILE_TITLE, s.OPEN_FAILED)
        if opening
        else (s.SAVE_FILE_TITLE, s.SAVE_FAILED)
    )
    _box(parent, _Icon.Critical, title, text, file_error_text(error)).exec()


def show_export_error(
    parent: QWidget | None,
    detail: str,
    title: str = s.EXPORT_PDF_TITLE,
    text: str = s.EXPORT_FAILED,
) -> None:
    """A report or drawing could not be written"""
    _box(parent, _Icon.Critical, title, text, detail).exec()


def confirm_overwrite(parent: QWidget | None, path: str) -> bool:
    """Ask before replacing an existing results bundle"""
    return _confirm(
        parent,
        _Icon.Warning,
        s.BUNDLE_TITLE,
        s.BUNDLE_OVERWRITE_QUESTION,
        s.BUNDLE_OVERWRITE_DETAIL.format(path=path),
        s.BUNDLE_REPLACE,
        True,
    )


def show_bundle_done(
    parent: QWidget | None, path: str, reports: int, sheets: int
) -> None:
    """The results bundle was written"""
    detail = s.BUNDLE_DONE_DETAIL.format(path=path, reports=reports, sheets=sheets)
    _box(parent, _Icon.Information, s.BUNDLE_TITLE, s.BUNDLE_DONE, detail).exec()


def show_isolated_not_verified(
    parent: QWidget | None, message: str, width_cm: float, height_cm: float
) -> None:
    """The isolated beam section could not be dimensioned"""
    detail = s.ISOLATED_NOT_VERIFIED_DETAIL.format(
        width=fmt_length_cm(width_cm),
        height=fmt_length_cm(height_cm),
        reason=translate(message),
    )
    _box(
        parent, _Icon.Warning, s.ISOLATED_TITLE, s.ISOLATED_NOT_VERIFIED, detail
    ).exec()


def show_isolated_input_error(parent: QWidget | None, message: str) -> None:
    _box(
        parent,
        _Icon.Critical,
        s.ISOLATED_TITLE,
        s.ISOLATED_INVALID_INPUT,
        translate(message),
    ).exec()


def show_about(parent: QWidget | None) -> None:
    QMessageBox.about(parent, s.ABOUT_TITLE, s.ABOUT_TEXT.format(version=app_version()))
