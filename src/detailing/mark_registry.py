from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.detailing.detailed_bar import DetailedBar
from src.detailing.detailed_clamps import DetailedClamps
from src.detailing.span_stirrups import SpanStirrups
from src.properties.steel import Steel
from src.structural_elements.rebar import HookGeometry

if TYPE_CHECKING:
    from src.detailing.detailing_beam import DetailingBeam

_NO_HOOK = (0.0, 0.0)


@dataclass(frozen=True, kw_only=True)
class BarKey:
    """What makes two longitudinal bars identical

    Attributes:
        diameter_mm: Bar diameter φ (mm).
        straight_length: Length of the straight segment (cm).
        hooks: Each end's bend diameter and extra cut length (cm), sorted, so a mirrored bar has the same key; zeros for an end without a hook.
    """

    diameter_mm: float
    steel: Steel
    straight_length: float  # cm
    hooks: tuple[tuple[float, float], tuple[float, float]]


@dataclass(frozen=True, kw_only=True)
class ClampKey:
    """What makes two clamps identical

    Attributes:
        diameter_mm: Clamp bar diameter φ (mm).
        leg_length: Length of each leg (cm).
        width: Width of the U (cm).
    """

    diameter_mm: float
    steel: Steel
    leg_length: float  # cm
    width: float  # cm


@dataclass(frozen=True, kw_only=True)
class StirrupKey:
    """What makes two stirrups identical

    Attributes:
        diameter_mm: Stirrup bar diameter φ_t (mm).
        width: Outer width of the stirrup (cm).
        height: Outer height of the stirrup (cm).
    """

    diameter_mm: float
    steel: Steel
    width: float  # cm
    height: float  # cm


def bar_key(bar: DetailedBar) -> BarKey:
    """Return the identity of a bar run's bars: diameter, steel, straight length and hooks, whichever end they are on"""
    first, second = sorted(
        (
            _hook_key(bar.left_hook, bar.left_hook_length),
            _hook_key(bar.right_hook, bar.right_hook_length),
        )
    )
    return BarKey(
        diameter_mm=bar.diameter_mm,
        steel=bar.steel,
        straight_length=bar.straight_length,
        hooks=(first, second),
    )


def _hook_key(hook: HookGeometry | None, length: float) -> tuple[float, float]:
    """Return a hook's bend diameter and cut length (cm)

    The tip length is left out: it is already in the whole-centimeter cut length, and a frame-joint tip carries fractions that do not exist on the built bar.
    """
    return _NO_HOOK if hook is None else (hook.pin_diameter, length)


def clamp_key(clamps: DetailedClamps) -> ClampKey:
    """Return the identity of a clamp set's clamps: diameter, steel, leg length and width"""
    return ClampKey(
        diameter_mm=clamps.diameter_mm,
        steel=clamps.steel,
        leg_length=clamps.leg_length,
        width=clamps.width,
    )


def stirrup_key(stirrups: SpanStirrups) -> StirrupKey:
    """Return the identity of a span's stirrups: diameter, steel and outer dimensions"""
    return StirrupKey(
        diameter_mm=stirrups.diameter_mm,
        steel=stirrups.steel,
        width=stirrups.outer_width,
        height=stirrups.outer_height,
    )


@dataclass
class MarkRegistry:
    """The bar marks of a pavement, shared by all of its beams

    Identical bars get the same mark in any beam, so the bar schedule counts them together. Marks are numbered in the order their keys are first seen.
    """

    _marks: dict[BarKey | ClampKey | StirrupKey, str] = field(
        default_factory=dict[BarKey | ClampKey | StirrupKey, str]
    )

    def mark_for(self, key: BarKey | ClampKey | StirrupKey) -> str:
        """Return a key's mark, giving it the next free one (N1, N2, …) if it is new"""
        return self._marks.setdefault(key, f"N{len(self._marks) + 1}")

    def assign(self, beam: DetailingBeam) -> None:
        """Write the marks of a beam's bars, clamps and stirrups, in that order

        Bars go bottom face first, by layer and left to right.
        """
        for is_bottom in (True, False):
            for bar in beam.bars_on_face(is_bottom):
                bar.mark = self.mark_for(bar_key(bar))
        for clamps in beam.clamps:
            clamps.mark = self.mark_for(clamp_key(clamps))
        for stirrups in beam.stirrups:
            stirrups.mark = self.mark_for(stirrup_key(stirrups))
