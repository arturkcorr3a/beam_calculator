from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.pavement.pillar import Pillar

_COORD_TOLERANCE = 0.01  # cm

# FIXME This was AI-generated code to make the UI work, improve it
@dataclass
class Slab:
    """
    Represents a two-way RC slab bounded by exactly 4 corner pillars.

    The 4 pillars must form an axis-aligned rectangle and all 4 perimeter
    beams must exist in the pavement. Load distribution (one-way vs two-way)
    is determined automatically from the lx/ly ratio per NBR 6118 §14.

    Material (concrete) and thickness are project-level settings. Surface loads will be defined separately when the load model is implemented.

    Attributes:
        id: Unique identifier (e.g. "S1")
        corner_pillar_ids: Tuple of 4 pillar IDs — order is arbitrary,
            the system identifies corners by their coordinates.
        thickness: Slab thickness (cm) — pre-calculated, see calculate_thickness()
    """
    id: str
    corner_pillar_ids: tuple[str, str, str, str]
    thickness: float = 0.0

    def calculate_thickness(self, pillar_registry: dict[str, Pillar]) -> float:
        """Placeholder for pre-dimensioning thickness calculation (to be implemented)."""
        raise NotImplementedError("Slab thickness pre-calculation is not yet implemented.")

    # ------------------------------------------------------------------
    # Derived geometry (populated by Pavement.validate())
    # ------------------------------------------------------------------

    def _corners(self, pillar_registry: dict[str, Pillar]) -> list[Pillar]:
        return [pillar_registry[pid] for pid in self.corner_pillar_ids]

    def dimensions(self, pillar_registry: dict[str, Pillar]) -> tuple[float, float]:
        """Returns (lx, ly) where lx ≤ ly (cm)."""
        corners = self._corners(pillar_registry)
        xs = sorted({p.x for p in corners})
        ys = sorted({p.y for p in corners})
        lx = xs[1] - xs[0]
        ly = ys[1] - ys[0]
        return (lx, ly) if lx <= ly else (ly, lx)

    def is_two_way(self, pillar_registry: dict[str, Pillar]) -> bool:
        """Returns True when lx/ly > 0.5 (NBR 6118 §14 criterion)."""
        lx, ly = self.dimensions(pillar_registry)
        return (lx / ly) > 0.5

    # ------------------------------------------------------------------
    # Validation helpers (called by Pavement.validate())
    # ------------------------------------------------------------------

    def validate_rectangle(self, pillar_registry: dict[str, Pillar]) -> None:
        """Checks that the 4 pillars form an axis-aligned rectangle."""
        if len(self.corner_pillar_ids) != 4:
            raise ValueError(
                f"Slab '{self.id}' must have exactly 4 corner pillars."
            )

        corners = self._corners(pillar_registry)
        xs = sorted({p.x for p in corners})
        ys = sorted({p.y for p in corners})

        if len(xs) != 2 or len(ys) != 2:
            raise ValueError(
                f"Slab '{self.id}': the 4 corner pillars must form an "
                f"axis-aligned rectangle (2 distinct x-coords and 2 distinct y-coords)."
            )

        expected_coords = {(xs[0], ys[0]), (xs[0], ys[1]),
                           (xs[1], ys[0]), (xs[1], ys[1])}
        actual_coords = {(p.x, p.y) for p in corners}

        if actual_coords != expected_coords:
            raise ValueError(
                f"Slab '{self.id}': pillar positions do not form a valid rectangle."
            )

    def validate_perimeter_beams(
        self,
        pillar_registry: dict[str, Pillar],
        beam_registry: dict,
    ) -> None:
        """
        Checks that all 4 perimeter beams exist.
        A perimeter beam exists when some ContinuousBeam contains both
        adjacent corner pillars as a consecutive span.
        """
        corners = self._corners(pillar_registry)
        xs = sorted({p.x for p in corners})
        ys = sorted({p.y for p in corners})

        # Identify the 4 corners by position
        def pillar_at(x: float, y: float) -> str:
            for p in corners:
                if abs(p.x - x) <= _COORD_TOLERANCE and abs(p.y - y) <= _COORD_TOLERANCE:
                    return p.id
            raise ValueError(
                f"Slab '{self.id}': no corner pillar found at ({x}, {y})."
            )

        bl = pillar_at(xs[0], ys[0])  # bottom-left
        br = pillar_at(xs[1], ys[0])  # bottom-right
        tl = pillar_at(xs[0], ys[1])  # top-left
        tr = pillar_at(xs[1], ys[1])  # top-right

        required_edges = [
            (bl, br, "bottom"),
            (tl, tr, "top"),
            (bl, tl, "left"),
            (br, tr, "right"),
        ]

        for pid_a, pid_b, side in required_edges:
            has_beam = any(
                b.contains_pillar_pair(pid_a, pid_b)
                for b in beam_registry.values()
            )
            if not has_beam:
                raise ValueError(
                    f"Slab '{self.id}': missing {side} perimeter beam "
                    f"between pillars '{pid_a}' and '{pid_b}'."
                )
