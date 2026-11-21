from dataclasses import dataclass

from src.properties.steel import Steel

SIDES = 2  # one bar on each side face of the web


@dataclass(kw_only=True)
class DetailedSkinBars:
    """The skin bars of one span: identical straight bars in rows, one bar on each side face per row

    Positions follow the beam's analysis axis.

    Attributes:
        start_pillar_id: Pillar at the span's start.
        end_pillar_id: Pillar at the span's end.
        diameter_mm: Bar diameter φ (mm).
        heights: Height of each row's bar axis, from the bottom face of the section, bottom to top (cm).
        start: Left end of the bars (cm).
        end: Right end of the bars (cm).
        mark: Bar mark (N1, N2, …), None until marks are assigned.

    References:
        ABNT NBR 6118:2026 — Section 17.3.5.2.3
    """

    start_pillar_id: str
    end_pillar_id: str
    diameter_mm: float
    steel: Steel
    heights: tuple[float, ...]  # cm
    start: float  # cm
    end: float  # cm
    mark: str | None = None

    def __post_init__(self) -> None:
        """Validate the rows and the extent

        Raises:
            ValueError: If there are no rows or the bars end before they start.
        """
        if not self.heights:
            raise ValueError("Skin bars need at least one row.")
        if self.end < self.start:
            raise ValueError(
                f"Skin bars cannot end before they start. Got start={self.start}, end={self.end} cm."
            )

    @property
    def span_name(self) -> str:
        """Return the span's name, e.g. "P1–P2" """
        return f"{self.start_pillar_id}–{self.end_pillar_id}"

    @property
    def quantity(self) -> int:
        """Return the number of bars: one on each side face per row"""
        return SIDES * len(self.heights)

    @property
    def straight_length(self) -> float:
        """Return the length of one bar (cm)"""
        return self.end - self.start

    @property
    def total_length(self) -> float:
        """Return the cut length of one bar (cm); the bars are straight, without hooks"""
        return self.straight_length
