"""Fixtures of the drawing tests: the hand-built V5 beam and resolved example pavements."""

import os
from collections.abc import Callable, Iterator
from dataclasses import fields
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

from src.config import APP_CONFIG  # noqa: E402
from src.detailing.detailing_beam import DetailingBeam  # noqa: E402
from src.logger import suppress_logging  # noqa: E402
from src.pavement_elements.pavement import Pavement  # noqa: E402
from src.persistency.yaml_io import load_pavement  # noqa: E402
from tests.drawing.v5 import build_v5  # noqa: E402

EXAMPLES = Path(__file__).parent.parent.parent / "resources" / "examples"


@pytest.fixture(autouse=True)
def _close_figures() -> Iterator[None]:  # pyright: ignore[reportUnusedFunction]
    """Close the matplotlib figures a test leaves open, so they do not pile up"""
    yield
    plt.close("all")


@pytest.fixture
def v5() -> DetailingBeam:
    """The hand-built V5 reference beam, with marks"""
    return build_v5()


def _resolved(build: Callable[[], Pavement]) -> Pavement:
    """Build a pavement and resolve it, leaving the global APP_CONFIG as it was

    Building sets fields of APP_CONFIG; they are restored right after the resolve, so
    the other tests keep the defaults. The log is silenced: pytest captures it, and a
    failing test would carry the whole resolve log in its report.
    """
    saved = {item.name: getattr(APP_CONFIG, item.name) for item in fields(APP_CONFIG)}
    try:
        with suppress_logging():
            pavement = build()
            pavement.resolve()
    finally:
        for name, value in saved.items():
            setattr(APP_CONFIG, name, value)
    return pavement


@pytest.fixture(scope="session")
def t_concreto2() -> Pavement:
    """The t_concreto2 pavement, resolved once per session (about a minute)

    Only for the full-pavement integration test: it is the biggest example. The other
    drawing tests use laje_rebaixada.
    """
    from src.examples.t_concreto2 import build_pavement

    return _resolved(build_pavement)


@pytest.fixture(scope="session")
def laje_rebaixada() -> Pavement:
    """The laje_rebaixada example (6 beams, 3 slabs), resolved once per session"""
    return _resolved(lambda: load_pavement(EXAMPLES / "pavimento_laje_rebaixada.yaml"))
