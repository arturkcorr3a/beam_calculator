"""Adjustable settings of the detailing drawings and the paper-to-model conversion"""

from dataclasses import dataclass

MM_PER_CM = 10.0


def paper(mm: float, scale: float = 50) -> float:
    """Return the model length of a paper length at the sheet scale

    Args:
        mm: Length on paper (mm).
        scale: Sheet scale denominator (1:scale).

    Returns:
        The model length (cm).
    """
    return mm * scale / MM_PER_CM


@dataclass(frozen=True)
class TextHeights:
    """Cap heights of the sheet's texts, on paper (mm)

    Attributes:
        beam_name: The beam's name in the title.
        beam_section: The b/h next to the beam's name.
        pillar: Pillar names and section letters.
        label: Bar labels, section titles, table titles and notes.
        small: Dimension numbers, zone texts, paper marks, section labels, tables and title block.
        title_block: Title of the title block.
    """

    beam_name: float = 6.0
    beam_section: float = 3.5
    pillar: float = 3.0
    label: float = 2.5
    small: float = 2.0
    title_block: float = 3.5


@dataclass(frozen=True)
class DrawingConfig:
    """Settings of a detailing sheet

    Lengths ending in ``_mm`` are on paper; the others are model lengths (cm).

    Attributes:
        sheet_scale: Scale denominator of the sheet and the elevation.
        section_scale: Scale denominator of the cross sections and the shapes.
        pillar_above: Stretch of pillar drawn above the beam (cm).
        pillar_below_min: Shortest stretch of pillar drawn below the beam (cm).
        pillar_below_margin: Pillar drawn below the lowest hook leg (cm).
        row_pitch_mm: Distance between bar rows (mm).
        row_clearance_mm: Smallest gap between the boxes of the items in the bar rows (mm).
        section_search_step: Step of the search for a cut position outside the laps (cm).
        section_edge_margin: Smallest distance between a cut and a pillar face (cm).
        arc_segments: Segments per quarter circle when an arc is drawn on screen.
        sheet_format: Paper format: "auto" picks the smallest that fits the drawing, or "A4", "A3", "A2", "A1", "A0".
        sheet_orientation: "paisagem" or "retrato"; "retrato" exists only for A4 (and makes "auto" try A4 portrait first).
        text_heights_mm: Cap heights of the texts (mm).
    """

    sheet_scale: float = 50
    section_scale: float = 25
    pillar_above: float = 20.0  # cm
    pillar_below_min: float = 20.0  # cm
    pillar_below_margin: float = 10.0  # cm
    row_pitch_mm: float = 10.0  # mm
    row_clearance_mm: float = 2.0  # mm
    section_search_step: float = 1.0  # cm
    section_edge_margin: float = 10.0  # cm
    arc_segments: int = 8
    sheet_format: str = "auto"
    sheet_orientation: str = "paisagem"
    text_heights_mm: TextHeights = TextHeights()

    @property
    def section_magnification(self) -> float:
        """Return the factor applied to the cross sections' geometry on the sheet"""
        return self.sheet_scale / self.section_scale

    def on_paper(self, length: float) -> float:
        """Return the paper length (mm) of a model length (cm) at this sheet's scale"""
        return length * MM_PER_CM / self.sheet_scale

    def paper(self, mm: float) -> float:
        """Return the model length (cm) of a paper length (mm) at this sheet's scale"""
        return paper(mm, self.sheet_scale)


DEFAULT_CONFIG = DrawingConfig()
