from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.pavement.pillar import Pillar

_COLLINEARITY_TOLERANCE = 0.01  # cm

# FIXME This was AI-generated code to make the UI work, improve it
# TODO mash it with RectangularBeam
@dataclass
class ContinuousBeam:
    """
    Represents a continuous RC beam running through 2 or more collinear pillars.

    pillar_ids lists the supporting pillars in order along the beam axis.
    The system auto-sorts them by coordinate on construction — users may supply
    them in any order.

    All pillars must share the same x-coordinate (Y-direction beam) or the same
    y-coordinate (X-direction beam). No diagonal beams are allowed.

    Material (concrete, steel) and cross-section height are project-level
    settings, not per-beam. Width is the only geometry input required here.

    Attributes:
        id: Automatically generated unique identifier (e.g. "V1")
        pillar_ids: Ordered list of pillar IDs along the beam axis (≥2)
        width: Cross-section width / bw (cm)
        height: Cross-section height / h (cm) — pre-calculated, see calculate_height()
    """
    pillar_ids: list[str]
    width: float
    height: float = 0.0
    id: str = field(default=None)

    _counter = count(1)  # Class-level counter for auto-generating IDs

    def __post_init__(self):
        if self.id is None:
            self.id = f"V{next(self._counter)}"  # Auto-generate ID if not provided

    def calculate_height(self) -> float:
        """Placeholder for pre-dimensioning height calculation (to be implemented)."""
        raise NotImplementedError("Beam height pre-calculation is not yet implemented.")

    def spans(self) -> list[tuple[str, str]]:
        """Returns each consecutive pillar pair as a (start_id, end_id) span."""
        return [(self.pillar_ids[i], self.pillar_ids[i + 1])
                for i in range(len(self.pillar_ids) - 1)]

    def contains_pillar_pair(self, pid_a: str, pid_b: str) -> bool:
        """Returns True if both pillar IDs appear as consecutive entries."""
        return (pid_a, pid_b) in self.spans() or (pid_b, pid_a) in self.spans()

    # ------------------------------------------------------------------
    # Validation helpers (called by Pavement.validate())
    # ------------------------------------------------------------------

    def validate_pillar_count(self) -> None:
        if len(self.pillar_ids) < 2:
            raise ValueError(
                f"Beam '{self.id}' must have at least 2 pillars, "
                f"got {len(self.pillar_ids)}."
            )

    def sort_and_validate_collinearity(self, pillar_registry: dict[str, Pillar]) -> None:
        """
        Sorts pillar_ids by coordinate and verifies collinearity.
        Mutates self.pillar_ids in-place.
        """
        pillars = [pillar_registry[pid] for pid in self.pillar_ids]

        xs = {p.x for p in pillars}
        ys = {p.y for p in pillars}

        x_spread = max(xs) - min(xs)
        y_spread = max(ys) - min(ys)

        if x_spread <= _COLLINEARITY_TOLERANCE and y_spread <= _COLLINEARITY_TOLERANCE:
            raise ValueError(
                f"Beam '{self.id}': all pillars are at the same position."
            )

        if x_spread <= _COLLINEARITY_TOLERANCE:
            # Vertical beam (Y-direction): sort by y
            self.pillar_ids = [
                p.id for p in sorted(pillars, key=lambda p: p.y)
            ]
        elif y_spread <= _COLLINEARITY_TOLERANCE:
            # Horizontal beam (X-direction): sort by x
            self.pillar_ids = [
                p.id for p in sorted(pillars, key=lambda p: p.x)
            ]
        else:
            raise ValueError(
                f"Beam '{self.id}' is diagonal: pillars must all share the same "
                f"x-coordinate or the same y-coordinate."
            )

    def validate_no_skipped_pillars(self, pillar_registry: dict[str, Pillar]) -> None:
        """
        Ensures no pillar on the same axis line is omitted from pillar_ids.
        Must be called after sort_and_validate_collinearity().
        """
        anchors = [pillar_registry[pid] for pid in self.pillar_ids]
        xs = {p.x for p in anchors}
        ys = {p.y for p in anchors}

        is_x_beam = len(ys) == 1
        fixed_coord = next(iter(ys)) if is_x_beam else next(iter(xs))

        # Find all pillars in the registry that lie on this axis line
        if is_x_beam:
            on_line = [
                p for p in pillar_registry.values()
                if abs(p.y - fixed_coord) <= _COLLINEARITY_TOLERANCE
            ]
            on_line.sort(key=lambda p: p.x)
            coord_key = lambda p: p.x  # noqa: E731
        else:
            on_line = [
                p for p in pillar_registry.values()
                if abs(p.x - fixed_coord) <= _COLLINEARITY_TOLERANCE
            ]
            on_line.sort(key=lambda p: p.y)
            coord_key = lambda p: p.y  # noqa: E731

        beam_ids = set(self.pillar_ids)
        start_coord = coord_key(pillar_registry[self.pillar_ids[0]])
        end_coord = coord_key(pillar_registry[self.pillar_ids[-1]])

        skipped = [
            p for p in on_line
            if p.id not in beam_ids
            and start_coord <= coord_key(p) <= end_coord
        ]

        if skipped:
            names = ", ".join(f"'{p.id}'" for p in skipped)
            raise ValueError(
                f"Beam '{self.id}' skips pillar(s) {names} that lie on the same "
                f"axis line between its endpoints."
            )
