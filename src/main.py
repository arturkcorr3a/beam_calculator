"""Entry point: launch the reinforced-concrete beam calculator GUI."""

import sys

from PySide6.QtWidgets import QApplication

from src.gui.beam_gui import BeamCalculatorWindow


def main() -> None:
    app = QApplication(sys.argv)
    window = BeamCalculatorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
