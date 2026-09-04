"""
Dark theme configuration for PySide6 GUI and Matplotlib figures.
Provides a cohesive, modern dark appearance across all platforms.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import matplotlib as mpl
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

if TYPE_CHECKING:
    from matplotlib.figure import Figure


# Theme color palette
DARK_BG_MAIN = "#1a1b26"       # Deep charcoal/navy background
DARK_BG_PANEL = "#24283b"      # Panel / group / card background
DARK_BG_INPUT = "#16161e"      # Input fields / canvas background
DARK_BG_HOVER = "#2f3549"      # Hover state for controls
DARK_BORDER = "#414868"        # Borders and dividers
DARK_BORDER_FOCUS = "#7aa2f7"  # Focused control border (accent)
DARK_TEXT_PRIMARY = "#c0caf5"  # High contrast text
DARK_TEXT_MUTED = "#7982a9"    # Secondary/dimmed text
DARK_ACCENT = "#7aa2f7"        # Primary blue/indigo accent
DARK_ACCENT_HOVER = "#89b4fa"  # Accent hover
DARK_SUCCESS = "#9ece6a"       # Soft green (valid / positive)
DARK_DANGER = "#f7768e"        # Soft red (error / negative)
DARK_WARNING = "#e0af68"       # Amber / warning


DARK_STYLESHEET = f"""
/* Global base */
QWidget {{
    background-color: {DARK_BG_MAIN};
    color: {DARK_TEXT_PRIMARY};
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}}

/* Main Window and Dialogs */
QMainWindow, QDialog {{
    background-color: {DARK_BG_MAIN};
}}

/* Menu Bar & Menus */
QMenuBar {{
    background-color: {DARK_BG_MAIN};
    color: {DARK_TEXT_PRIMARY};
    border-bottom: 1px solid {DARK_BORDER};
    padding: 2px;
}}
QMenuBar::item {{
    background: transparent;
    padding: 4px 8px;
    border-radius: 4px;
}}
QMenuBar::item:selected {{
    background-color: {DARK_BG_HOVER};
}}
QMenu {{
    background-color: {DARK_BG_PANEL};
    color: {DARK_TEXT_PRIMARY};
    border: 1px solid {DARK_BORDER};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 20px 6px 12px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {DARK_ACCENT};
    color: #ffffff;
}}

/* Group Boxes */
QGroupBox {{
    background-color: {DARK_BG_PANEL};
    border: 1px solid {DARK_BORDER};
    border-radius: 8px;
    margin-top: 1.2em;
    padding-top: 14px;
    padding-bottom: 10px;
    padding-left: 10px;
    padding-right: 10px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 4px;
    color: {DARK_ACCENT};
    background-color: {DARK_BG_PANEL};
    border-radius: 3px;
}}

/* Input controls */
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {{
    background-color: {DARK_BG_INPUT};
    color: {DARK_TEXT_PRIMARY};
    border: 1px solid {DARK_BORDER};
    border-radius: 5px;
    padding: 4px 8px;
    selection-background-color: {DARK_ACCENT};
    selection-color: #ffffff;
    min-height: 22px;
}}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {DARK_BORDER_FOCUS};
}}
QDoubleSpinBox::up-button, QSpinBox::up-button,
QDoubleSpinBox::down-button, QSpinBox::down-button {{
    background: {DARK_BG_HOVER};
    border: none;
    width: 16px;
}}
QDoubleSpinBox::up-button:hover, QSpinBox::up-button:hover,
QDoubleSpinBox::down-button:hover, QSpinBox::down-button:hover {{
    background: {DARK_BORDER};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {DARK_BG_PANEL};
    color: {DARK_TEXT_PRIMARY};
    selection-background-color: {DARK_ACCENT};
    selection-color: #ffffff;
    border: 1px solid {DARK_BORDER};
    border-radius: 4px;
    padding: 4px;
}}

/* Buttons */
QPushButton {{
    background-color: {DARK_BG_HOVER};
    color: {DARK_TEXT_PRIMARY};
    border: 1px solid {DARK_BORDER};
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: #3b4261;
    border-color: {DARK_BORDER_FOCUS};
}}
QPushButton:pressed {{
    background-color: #1f2335;
}}
QPushButton:disabled {{
    background-color: {DARK_BG_INPUT};
    color: {DARK_TEXT_MUTED};
    border-color: #2a2e3f;
}}

/* Tab Widget */
QTabWidget::pane {{
    border: 1px solid {DARK_BORDER};
    border-radius: 6px;
    background-color: {DARK_BG_PANEL};
    top: -1px;
}}
QTabBar::tab {{
    background-color: {DARK_BG_MAIN};
    color: {DARK_TEXT_MUTED};
    border: 1px solid {DARK_BORDER};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 6px 14px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: {DARK_BG_PANEL};
    color: {DARK_TEXT_PRIMARY};
    font-weight: 600;
    border-bottom: 1px solid {DARK_BG_PANEL};
}}
QTabBar::tab:hover:!selected {{
    background-color: {DARK_BG_HOVER};
}}

/* Plain Text & List Views */
QPlainTextEdit, QTextEdit, QListWidget {{
    background-color: {DARK_BG_INPUT};
    color: {DARK_TEXT_PRIMARY};
    border: 1px solid {DARK_BORDER};
    border-radius: 6px;
    padding: 6px;
    selection-background-color: {DARK_ACCENT};
    selection-color: #ffffff;
}}
QListWidget::item {{
    padding: 4px 6px;
    border-radius: 4px;
}}
QListWidget::item:selected {{
    background-color: {DARK_BG_HOVER};
    color: {DARK_ACCENT};
}}

/* Splitters & Scrollbars */
QSplitter::handle {{
    background-color: {DARK_BORDER};
}}
QSplitter::handle:horizontal {{
    width: 2px;
}}
QSplitter::handle:vertical {{
    height: 2px;
}}

QScrollBar:vertical {{
    background: {DARK_BG_MAIN};
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: {DARK_BORDER};
    min-height: 20px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background: {DARK_TEXT_MUTED};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
    height: 0px;
}}

/* Tooltips */
QToolTip {{
    background-color: {DARK_BG_PANEL};
    color: {DARK_TEXT_PRIMARY};
    border: 1px solid {DARK_BORDER};
    border-radius: 4px;
    padding: 4px 8px;
}}
"""


def apply_dark_theme(app: QApplication | None = None) -> None:
    """Apply the dark theme to the QApplication and configure Matplotlib dark defaults."""
    if app is None:
        app = QApplication.instance()
        if app is None:
            return

    # Use Fusion style as the base for cross-platform consistency
    app.setStyle("Fusion")

    # Dark QPalette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(DARK_BG_MAIN))
    palette.setColor(QPalette.WindowText, QColor(DARK_TEXT_PRIMARY))
    palette.setColor(QPalette.Base, QColor(DARK_BG_INPUT))
    palette.setColor(QPalette.AlternateBase, QColor(DARK_BG_PANEL))
    palette.setColor(QPalette.ToolTipBase, QColor(DARK_BG_PANEL))
    palette.setColor(QPalette.ToolTipText, QColor(DARK_TEXT_PRIMARY))
    palette.setColor(QPalette.Text, QColor(DARK_TEXT_PRIMARY))
    palette.setColor(QPalette.Button, QColor(DARK_BG_PANEL))
    palette.setColor(QPalette.ButtonText, QColor(DARK_TEXT_PRIMARY))
    palette.setColor(QPalette.BrightText, QColor(DARK_DANGER))
    palette.setColor(QPalette.Link, QColor(DARK_ACCENT))
    palette.setColor(QPalette.Highlight, QColor(DARK_ACCENT))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(DARK_TEXT_MUTED))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(DARK_TEXT_MUTED))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(DARK_TEXT_MUTED))
    app.setPalette(palette)

    # Apply CSS rules for refined spacing, borders and control states
    app.setStyleSheet(DARK_STYLESHEET)

    # Configure Matplotlib dark defaults
    mpl.rcParams["figure.facecolor"] = DARK_BG_MAIN
    mpl.rcParams["figure.edgecolor"] = DARK_BG_MAIN
    mpl.rcParams["axes.facecolor"] = DARK_BG_INPUT
    mpl.rcParams["axes.edgecolor"] = DARK_BORDER
    mpl.rcParams["axes.labelcolor"] = DARK_TEXT_PRIMARY
    mpl.rcParams["text.color"] = DARK_TEXT_PRIMARY
    mpl.rcParams["xtick.color"] = DARK_TEXT_MUTED
    mpl.rcParams["ytick.color"] = DARK_TEXT_MUTED
    mpl.rcParams["grid.color"] = DARK_BORDER
    mpl.rcParams["grid.alpha"] = 0.35
    mpl.rcParams["legend.facecolor"] = DARK_BG_PANEL
    mpl.rcParams["legend.edgecolor"] = DARK_BORDER
    mpl.rcParams["legend.labelcolor"] = DARK_TEXT_PRIMARY


def style_figure(fig: Figure, bg_color: str = DARK_BG_MAIN) -> None:
    """Convenience helper to set figure background color."""
    fig.patch.set_facecolor(bg_color)
