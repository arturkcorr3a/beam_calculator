"""Every QAction of the main window: text, icon, shortcut and objectName."""

from dataclasses import dataclass

from PySide6.QtCore import QObject
from PySide6.QtGui import QAction, QKeySequence

from pavement_ui.presentation.main_window.action_rules import (
    ActionContext,
    ActionId,
    enabled_actions,
)
from pavement_ui.presentation.text.strings import main_window as s
from pavement_ui.presentation.theme import tokens
from pavement_ui.presentation.theme.icons import IconName, icon


@dataclass(frozen=True, slots=True)
class _ActionSpec:
    object_name: str
    text: str
    shortcut: str = ""
    icon_name: IconName | None = None
    icon_color: str = tokens.TEXT


_SPECS: dict[ActionId, _ActionSpec] = {
    ActionId.NEW: _ActionSpec("actNew", s.NEW, "Ctrl+N", "new"),
    ActionId.OPEN: _ActionSpec("actOpen", s.OPEN, "Ctrl+O", "open"),
    ActionId.OPEN_EXAMPLE: _ActionSpec("actOpenExample", s.OPEN_EXAMPLE),
    ActionId.SAVE: _ActionSpec("actSave", s.SAVE, "Ctrl+S", "save"),
    ActionId.SAVE_AS: _ActionSpec("actSaveAs", s.SAVE_AS, "Ctrl+Shift+S"),
    ActionId.QUIT: _ActionSpec("actQuit", s.QUIT, "Ctrl+Q"),
    ActionId.FOCUS_PILLARS: _ActionSpec("actFocusPillars", s.FOCUS_PILLARS, "Ctrl+1"),
    ActionId.FOCUS_BEAMS: _ActionSpec("actFocusBeams", s.FOCUS_BEAMS, "Ctrl+2"),
    ActionId.FOCUS_SLABS: _ActionSpec("actFocusSlabs", s.FOCUS_SLABS, "Ctrl+3"),
    ActionId.CLEAR: _ActionSpec("actClear", s.CLEAR, "", "trash", tokens.ERROR),
    ActionId.VALIDATE: _ActionSpec("actValidate", s.VALIDATE, "F5", "validate"),
    ActionId.DESIGN: _ActionSpec("actDesign", s.DESIGN, "F6", "design"),
    ActionId.RESULTS: _ActionSpec("actResults", s.RESULTS, "Ctrl+R", "results"),
    ActionId.CONFIG: _ActionSpec("actConfig", s.CONFIG, "Ctrl+,", "settings"),
    ActionId.ISOLATED: _ActionSpec("actIsolated", s.ISOLATED, "", "isolated_beam"),
    ActionId.ABOUT: _ActionSpec("actAbout", s.ABOUT),
}


class AppActions(QObject):
    """Owns the actions; menus, toolbar and controllers look them up by id"""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._actions = {
            action_id: self._create(spec) for action_id, spec in _SPECS.items()
        }

    def _create(self, spec: _ActionSpec) -> QAction:
        action = QAction(spec.text, self)
        action.setObjectName(spec.object_name)
        if spec.shortcut:
            action.setShortcut(QKeySequence(spec.shortcut))
        if spec.icon_name is not None:
            action.setIcon(icon(spec.icon_name, spec.icon_color))
        return action

    def __getitem__(self, action_id: ActionId) -> QAction:
        return self._actions[action_id]

    def update_enabled_state(self, context: ActionContext) -> None:
        """Enable exactly the actions allowed in context"""
        enabled = enabled_actions(context)
        for action_id, action in self._actions.items():
            action.setEnabled(action_id in enabled)
