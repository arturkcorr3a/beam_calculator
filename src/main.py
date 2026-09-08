# REVIEW AI-Generated; review when done
"""Entry point: launch the reinforced-concrete beam calculator GUI."""

import sys

from PySide6.QtWidgets import QApplication

from src.gui.pavement_gui import PavementWindow
from src.gui.theme import apply_dark_theme


def main() -> None:
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    window = PavementWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
