"""Tests for src/detailing/post_processor.py."""

import types
from typing import cast

import pytest

import src.detailing.post_processor as post_processor
from src.detailing.detailing_beam import DetailingBeam
from src.pavement_elements.continuous_beam import ContinuousBeam


class TestDetailBeam:
    """detail_beam builds the detailing and runs every step on it, in order."""

    def test_runs_steps_in_order_on_built_beam(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        built = cast(
            DetailingBeam, types.SimpleNamespace(bars=[], clamps=[], stirrups=[])
        )
        calls: list[tuple[str, DetailingBeam]] = []

        def build(beam: ContinuousBeam) -> DetailingBeam:
            return built

        def first(detailing: DetailingBeam) -> None:
            calls.append(("first", detailing))

        def second(detailing: DetailingBeam) -> None:
            calls.append(("second", detailing))

        monkeypatch.setattr(post_processor, "build_detailing_beam", build)
        monkeypatch.setattr(post_processor, "_STEPS", (first, second))

        result = post_processor.detail_beam(
            cast(ContinuousBeam, types.SimpleNamespace())
        )

        assert result is built, "detail_beam should return the built detailing"
        assert calls == [("first", built), ("second", built)], (
            "Steps should run in order on the built detailing"
        )
