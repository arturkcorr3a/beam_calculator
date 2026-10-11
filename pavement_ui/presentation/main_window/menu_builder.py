"""Menu bar and toolbar of the main window, built from AppActions."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QMainWindow, QToolBar

from pavement_ui.presentation.main_window.action_rules import ActionId as A
from pavement_ui.presentation.main_window.app_actions import AppActions
from pavement_ui.presentation.text.strings import main_window as s
from pavement_ui.presentation.widgets.variants import set_variant

type _Group = tuple[A, ...]

_MENUS: tuple[tuple[str, tuple[_Group, ...]], ...] = (
    (s.MENU_FILE, ((A.NEW, A.OPEN, A.SAVE, A.SAVE_AS), (A.QUIT,))),
    (s.MENU_PAVEMENT, ((A.FOCUS_PILLARS, A.FOCUS_BEAMS, A.FOCUS_SLABS), (A.CLEAR,))),
    (s.MENU_CALCULATION, ((A.VALIDATE, A.DESIGN, A.RESULTS),)),
    (s.MENU_TOOLS, ((A.CONFIG, A.ISOLATED),)),
    (s.MENU_HELP, ((A.ABOUT,),)),
)
_TOOLBAR: tuple[_Group, ...] = (
    (A.NEW, A.OPEN, A.SAVE),
    (A.CONFIG,),
    (A.VALIDATE, A.DESIGN, A.RESULTS),
    (A.CLEAR,),
    (A.ISOLATED,),
)
_ICON_SIZE_PX = 18


def build_menus(window: QMainWindow, actions: AppActions) -> None:
    """Fill the window's menu bar; groups are separated by a line"""
    for title, groups in _MENUS:
        menu = window.menuBar().addMenu(title)
        for index, group in enumerate(groups):
            if index:
                menu.addSeparator()
            for action_id in group:
                menu.addAction(actions[action_id])


def build_toolbar(window: QMainWindow, actions: AppActions) -> QToolBar:
    """Add the toolbar: icon and text side by side, Dimensionar as primary"""
    toolbar = window.addToolBar(s.TOOLBAR)
    toolbar.setObjectName("mainToolbar")
    toolbar.setMovable(False)
    toolbar.setIconSize(QSize(_ICON_SIZE_PX, _ICON_SIZE_PX))
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    for index, group in enumerate(_TOOLBAR):
        if index:
            toolbar.addSeparator()
        for action_id in group:
            toolbar.addAction(actions[action_id])
    set_variant(toolbar.widgetForAction(actions[A.DESIGN]), "primary")
    set_variant(toolbar.widgetForAction(actions[A.CLEAR]), "destructive")
    return toolbar
