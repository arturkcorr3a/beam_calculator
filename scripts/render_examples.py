"""Render the t_concreto2 drawings for a visual check against the mockups (not run in CI)

Writes ``out/drawing/V1.png`` … ``V10.png`` and ``out/drawing/t_concreto2.dxf``.

Usage, from the repository root::

    PYTHONPATH=. .venv/bin/python scripts/render_examples.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

from src.config import APP_CONFIG  # noqa: E402
from src.drawing.api import (  # noqa: E402
    PNG_DPI,
    beam_figure,
    export_pavement_dxf,
    pavement_detailings,
)
from src.logger import LogLevel, configure_logger  # noqa: E402
from src.persistency import load_pavement  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SAVED = ROOT / "saved" / "t_concreto2.yaml"
OUT = ROOT / "out" / "drawing"
NAME = "t_concreto2"


def main() -> None:
    """Resolve t_concreto2 from saved/ and write its beam PNGs and its pavement DXF"""
    APP_CONFIG.log_level = LogLevel.DISABLED
    configure_logger(APP_CONFIG.log_level, APP_CONFIG.log_output)
    pavement = load_pavement(SAVED)
    pavement.resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    for detailing in pavement_detailings(pavement):
        figure = beam_figure(detailing, pavement_name=NAME)
        path = OUT / f"{detailing.beam_id}.png"
        figure.savefig(path, dpi=PNG_DPI)  # pyright: ignore[reportUnknownMemberType]
        plt.close(figure)
        print(path)
    print(export_pavement_dxf(pavement, OUT / f"{NAME}.dxf", pavement_name=NAME))


if __name__ == "__main__":
    main()
