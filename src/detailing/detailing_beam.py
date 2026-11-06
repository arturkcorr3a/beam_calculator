from dataclasses import dataclass, field

from src.analysis.beam_analysis import BeamAnalysis
from src.detailing.detailed_bar import DetailedBar
from src.detailing.detailed_clamps import DetailedClamps
from src.detailing.detailing_report import build_report
from src.detailing.lap_splice import LapSplice
from src.detailing.span_stirrups import SpanStirrups
from src.properties.steel import Steel
from src.structural_elements.support import Support


@dataclass(kw_only=True)
class DetailingBeam:
    """The bars of a dimensioned beam, as they are built

    A separate copy of the beam's reinforcement, refined by the post-processing steps without touching the design objects. Positions follow the analysis axis: with the effective span's 0.3 h cap disabled, it is the physical position from the first pillar's axis, so the beam runs from the first support's left face to the last support's right face.

    Attributes:
        width: Section width b_w (cm).
        height: Section height h (cm).
        nominal_covering: Nominal cover c_nom (cm).
        supports: Extent of each pillar along the beam, left to right.
        lap_splices: Lap splices between bar runs, in the order they were made.
        analysis: Structural analysis of the dimensioned beam, used to place splices where the bars are least tensioned; None when not built from a dimensioned beam.
    """

    beam_id: str
    width: float  # cm
    height: float  # cm
    nominal_covering: float  # cm
    steel: Steel
    supports: tuple[Support, ...]
    bars: list[DetailedBar] = field(default_factory=list[DetailedBar])
    clamps: list[DetailedClamps] = field(default_factory=list[DetailedClamps])
    stirrups: list[SpanStirrups] = field(default_factory=list[SpanStirrups])
    lap_splices: list[LapSplice] = field(default_factory=list[LapSplice])
    analysis: BeamAnalysis | None = None

    def __post_init__(self) -> None:
        """Validate the supports

        Raises:
            ValueError: If there are fewer than two supports.
        """
        if len(self.supports) < 2:
            raise ValueError(
                f"Beam '{self.beam_id}' needs at least 2 supports to be detailed."
            )

    @property
    def start(self) -> float:
        """Return the beam's left end: the first pillar's outer face (cm)"""
        return self.supports[0].left

    @property
    def end(self) -> float:
        """Return the beam's right end: the last pillar's outer face (cm)"""
        return self.supports[-1].right

    def bars_on_face(self, is_bottom: bool) -> list[DetailedBar]:
        """Return the bars on one face, by layer and then left to right

        Args:
            is_bottom: Whether to read the bottom face; otherwise the top.
        """
        return sorted(
            (bar for bar in self.bars if bar.is_bottom == is_bottom),
            key=lambda bar: (bar.layer_index, bar.start, bar.end),
        )

    def bars_at(self, position: float, is_bottom: bool) -> list[DetailedBar]:
        """Return the bars on one face whose straight segment covers a position

        Args:
            position: Position along the beam (cm).
            is_bottom: Whether to read the bottom face; otherwise the top.
        """
        return [
            bar
            for bar in self.bars_on_face(is_bottom)
            if bar.start <= position <= bar.end
        ]

    def report(self) -> str:
        """Describe the detailed bars, clamps and stirrups as plain text"""
        return build_report(self)
