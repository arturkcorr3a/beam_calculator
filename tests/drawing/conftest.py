"""Fixtures of the drawing tests: the hand-built V5 beam and the resolved t_concreto2."""

import os
from dataclasses import fields

os.environ.setdefault("MPLBACKEND", "Agg")

import pytest  # noqa: E402

from src.config import APP_CONFIG  # noqa: E402
from src.detailing.detailing_beam import DetailingBeam  # noqa: E402
from src.pavement_elements.pavement import Pavement  # noqa: E402
from tests.drawing.v5 import build_v5  # noqa: E402


@pytest.fixture
def v5() -> DetailingBeam:
    """The V5 beam of the mockups (spec Appendix A), with marks"""
    return build_v5()


@pytest.fixture(scope="session")
def t_concreto2() -> Pavement:
    """The t_concreto2 pavement, resolved once per session (about a minute)

    Building it sets fields of the global APP_CONFIG; they are restored right after
    the resolve, so the other tests keep the defaults.
    """
    from src.examples.t_concreto2 import build_pavement

    saved = {item.name: getattr(APP_CONFIG, item.name) for item in fields(APP_CONFIG)}
    try:
        pavement = build_pavement()
        pavement.resolve()
    finally:
        for name, value in saved.items():
            setattr(APP_CONFIG, name, value)
    return pavement
