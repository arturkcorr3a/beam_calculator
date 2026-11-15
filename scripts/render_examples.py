"""Render the drawings of the pavimento_residencial example (t_concreto2) for a visual check (not run in CI)

Writes one sheet per beam, ``out/drawing/V1.dxf``/``.png``/``.pdf`` … ``V10.*``,
and ``out/drawing/pavement.pdf`` with every sheet, one per page.

Usage, from the repository root::

    PYTHONPATH=. .venv/bin/python scripts/render_examples.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from src.config import APP_CONFIG  # noqa: E402
from src.drawing.api import save_pavement as save_drawings  # noqa: E402
from src.logger import LogLevel, configure_logger  # noqa: E402
from src.persistency import load_pavement  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SAVED = ROOT / "resources" / "examples" / "pavimento_residencial.yaml"
OUT = ROOT / "out" / "drawing"
NAME = "pavimento_residencial"


def main() -> None:
    """Resolve the example from resources/examples/ and write its beam sheets"""
    APP_CONFIG.log_level = LogLevel.DISABLED
    configure_logger(APP_CONFIG.log_level, APP_CONFIG.log_output)
    pavement = load_pavement(SAVED)
    pavement.resolve()
    for path in save_drawings(pavement, OUT, pavement_name=NAME):
        print(path)


if __name__ == "__main__":
    main()
