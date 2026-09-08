# REVIEW AI-Generated; review when done
"""Entry point: launch the reinforced-concrete beam calculator GUI."""

import sys

from PySide6.QtWidgets import QApplication

from src.gui.beam_gui import BeamCalculatorWindow
from src.gui.theme import apply_dark_theme


def main() -> None:
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    window = BeamCalculatorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
