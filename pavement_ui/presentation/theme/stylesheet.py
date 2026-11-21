"""Application stylesheet (QSS), generated from the design tokens."""

from pavement_ui.presentation.theme import tokens as t


def build_stylesheet() -> str:
    """Build the application-wide QSS from the design tokens

    Widgets opt into variants through ``objectName`` or the ``variant``
    dynamic property: ``primary`` and ``destructive`` buttons, and ``hint``
    labels.

    Returns:
        The stylesheet text for ``QApplication.setStyleSheet``.
    """
    return f"""
QWidget {{
    color: {t.TEXT};
}}
QMainWindow, QDialog {{
    background: {t.WINDOW_BG};
}}
QMenuBar, QToolBar {{
    background: {t.CHROME_BG};
    border-bottom: 1px solid {t.BORDER};
}}
QToolBar {{
    spacing: {t.SPACING_PX}px;
    padding: 2px {t.SPACING_PX}px;
}}
QStatusBar {{
    background: {t.STATUS_BG};
    border-top: 1px solid {t.BORDER};
}}
QGroupBox {{
    background: {t.CHROME_BG};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS_PX}px;
    margin-top: 14px;
    padding: {t.MARGIN_PX}px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: {t.MARGIN_PX}px;
    padding: 0 4px;
    font-weight: 600;
}}
QLineEdit, QComboBox {{
    background: {t.SURFACE};
    border: 1px solid {t.BORDER_INPUT};
    border-radius: {t.RADIUS_PX}px;
    padding: 3px 6px;
    min-height: 20px;
}}
QListWidget {{
    background: {t.SURFACE};
    border: 1px solid {t.BORDER_INPUT};
    border-radius: {t.RADIUS_PX}px;
}}
QListWidget:focus {{
    border-color: {t.ACCENT};
}}
QListWidget::item:disabled {{
    color: {t.TEXT_MUTED};
}}
QSpinBox, QDoubleSpinBox {{
    background: {t.SURFACE};
    border: 1px solid {t.BORDER_INPUT};
    border-radius: {t.RADIUS_PX}px;
    min-height: 26px;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {t.ACCENT};
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
    background: {t.CHROME_BG};
    border-color: {t.BORDER};
    color: {t.TEXT_MUTED};
}}
QLabel:disabled {{
    color: {t.TEXT_MUTED};
}}
QPushButton {{
    background: {t.SURFACE};
    border: 1px solid {t.BORDER_INPUT};
    border-radius: {t.RADIUS_PX}px;
    padding: 4px 12px;
}}
QPushButton:hover {{
    border-color: {t.ACCENT};
}}
QPushButton[variant="primary"] {{
    background: {t.ACCENT};
    border-color: {t.ACCENT};
    color: {t.SURFACE};
    font-weight: 600;
}}
QPushButton[variant="primary"]:hover {{
    background: {t.ACCENT_HOVER};
}}
QPushButton[variant="destructive"] {{
    color: {t.ERROR};
}}
QPushButton:disabled, QPushButton[variant="primary"]:disabled {{
    background: {t.CHROME_BG};
    border-color: {t.BORDER};
    color: {t.TEXT_MUTED};
}}
QToolButton {{
    padding: 3px 6px;
    border: 1px solid transparent;
    border-radius: {t.RADIUS_PX}px;
}}
QToolButton:hover {{
    border-color: {t.BORDER_INPUT};
    background: {t.SURFACE};
}}
QToolButton[variant="primary"] {{
    background: {t.SELECTION_ROW};
    border-color: {t.ACCENT};
    color: {t.ACCENT};
    font-weight: 600;
}}
QToolButton[variant="destructive"] {{
    color: {t.ERROR};
}}
QLabel#hint {{
    color: {t.TEXT_MUTED};
}}
QTableView {{
    background: {t.SURFACE};
    border: 1px solid {t.BORDER};
    gridline-color: {t.BORDER};
    selection-background-color: {t.SELECTION_ROW};
    selection-color: {t.TEXT};
}}
QHeaderView::section {{
    background: {t.CHROME_BG};
    border: none;
    border-right: 1px solid {t.BORDER};
    border-bottom: 1px solid {t.BORDER};
    padding: 4px 6px;
    font-weight: 600;
}}
QTabWidget::pane {{
    background: {t.SURFACE};
    border: 1px solid {t.BORDER};
}}
QTabBar::tab {{
    background: {t.CHROME_BG};
    border: 1px solid {t.BORDER};
    padding: 5px 12px;
}}
QTabBar::tab:selected {{
    background: {t.SURFACE};
    border-bottom-color: {t.SURFACE};
    color: {t.ACCENT};
    font-weight: 600;
}}
QSplitter::handle {{
    background: {t.WINDOW_BG};
}}
"""
