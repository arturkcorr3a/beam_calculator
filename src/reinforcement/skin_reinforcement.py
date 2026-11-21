from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import ceil
from typing import TYPE_CHECKING

from src.logger import log_element, log_operation, logger_label
from src.properties.section_properties_calculator import (
    SectionPropertiesCalculator as section,
)
from src.properties.steel import Steel

if TYPE_CHECKING:
    from src.calculators.rebar_calculator import RebarCalculator
    from src.structural_elements.rectangular_beam import RectangularBeam

MIN_REQUIRED_HEIGHT = 60.0  # cm, at or below it the skin reinforcement may be omitted
MIN_RATIO = 0.10 / 100  # of the web area, per face
MAX_AREA_PER_HEIGHT = 5.0 / 100  # cm² per cm of web height (5 cm²/m), per face
MAX_SPACING = 20.0  # cm
MAX_SPACING_DEPTH_RATIO = 1 / 3  # of the effective depth d
MAX_SPACING_DIAMETER_RATIO = 15  # bar diameters, in the tensioned zone
ALLOWED_STEELS = (Steel.CA50, Steel.CA60)


@dataclass(frozen=True, slots=True)
class SkinLayout:
    """Bars of the skin reinforcement on each face of the web

    Attributes:
        diameter_mm: Bar diameter (mm).
        bars_per_face: Number of bars on each face of the web.
        spacing: Distance between consecutive bars, and from the end bars to the band edges (cm).
        band_start: Band edge on the bottom bars, from the bottom face (cm).
        band_end: Band edge on the top bars, from the bottom face (cm).
    """

    diameter_mm: float
    bars_per_face: int
    spacing: float
    band_start: float
    band_end: float

    @property
    def area_per_face(self) -> float:
        """Provided area on each face of the web (cm²)"""
        bar_area = section.circular_cross_sectional_area(self.diameter_mm / 10)  # cm²
        return self.bars_per_face * bar_area

    @property
    def band_height(self) -> float:
        """Height of the band between the bottom and top bars (cm)"""
        return self.band_end - self.band_start


@logger_label("Skin Reinforcement - {id}")
class SkinReinforcement:
    """Lateral (skin) reinforcement of one span, on each face of the web

    The bars fill the whole web height left free by the longitudinal bars: from the last bottom layer to the last top layer. The main tension and compression bars are not counted in its area.

    Attributes:
        layout: The chosen bars; None until ``choose`` runs.

    References:
        ABNT NBR 6118:2026 — Section 17.3.5.2.3
    """

    def __init__(self, beam: RectangularBeam, id: str = "") -> None:
        """Start a span's skin reinforcement, with no bars chosen yet

        Raises:
            ValueError: If the beam's steel is neither CA-50 nor CA-60.

        References:
            ABNT NBR 6118:2026 — Section 17.3.5.2.3
        """
        if beam.steel not in ALLOWED_STEELS:
            raise ValueError(
                f"Skin reinforcement must be CA-50 or CA-60. Got {beam.steel.name}."
            )
        self.beam = beam
        self.steel = beam.steel
        self.layout: SkinLayout | None = None
        self.id = id

    @staticmethod
    def is_required(height: float) -> bool:
        """Whether a beam of this height (cm) needs skin reinforcement

        References:
            ABNT NBR 6118:2026 — Section 17.3.5.2.3
        """
        return height > MIN_REQUIRED_HEIGHT

    @property
    def required_area(self) -> float:
        """Minimum area on each face of the web (cm²)

        A ratio of the web area, capped at a fixed area per meter of web height.

        References:
            ABNT NBR 6118:2026 — Section 17.3.5.2.3
        """
        web_area = self.beam.width * self.beam.height  # cm²
        return min(MIN_RATIO * web_area, MAX_AREA_PER_HEIGHT * self.beam.height)

    @staticmethod
    def max_spacing(effective_depth: float, diameter_mm: float) -> float:
        """Largest spacing between skin bars (cm)

        The least of a fixed limit, a third of d and fifteen bar diameters. The last one is set for the tensioned zone; it is applied to the whole band, which keeps one spacing over the web height.

        Args:
            effective_depth: Effective depth d of the section (cm).
            diameter_mm: Skin bar diameter (mm).

        References:
            ABNT NBR 6118:2026 — Section 17.3.5.2.3
            ABNT NBR 6118:2026 — Section 18.3.5
            ABNT NBR 6118:2026 — Section 17.3.3.2
        """
        return min(
            MAX_SPACING,
            MAX_SPACING_DEPTH_RATIO * effective_depth,
            MAX_SPACING_DIAMETER_RATIO * diameter_mm / 10,
        )

    def choose(self, calculators: Sequence[RebarCalculator]) -> SkinLayout:
        """Choose the span's skin bars from its dimensioned interest points

        Each point gets its own layout (see ``choose_for``), between its tensioned and compressed bars; the span keeps the one with the most bars per face, and on a tie the larger area.

        Args:
            calculators: The span's coordinated calculators.

        Raises:
            ValueError: If no calculator is given, or propagated from ``choose_for``.
        """
        if not calculators:
            raise ValueError("Skin reinforcement needs at least one interest point.")
        layouts = [self._choose_for_point(calculator) for calculator in calculators]
        self.layout = max(
            layouts, key=lambda layout: (layout.bars_per_face, layout.area_per_face)
        )
        log_element(
            f"Skin reinforcement: 2 x {self.layout.bars_per_face} φ{self.layout.diameter_mm:g} c/{self.layout.spacing:.1f} cm"
        )
        return self.layout

    def _choose_for_point(self, calculator: RebarCalculator) -> SkinLayout:
        """Choose the skin bars between a point's tensioned and compressed bars"""
        tensioned = calculator.tensioned_reinforcement
        compressed = calculator.compressed_reinforcement
        bottom, top = (
            (tensioned, compressed)
            if tensioned.is_bottom_reinforcement
            else (compressed, tensioned)
        )
        return self.choose_for(
            effective_depth=calculator.d,
            bottom_extent=bottom.face_extent(),
            top_extent=top.face_extent(),
        )

    def choose_for(
        self, *, effective_depth: float, bottom_extent: float, top_extent: float
    ) -> SkinLayout:
        """Choose the skin bars for one section

        For each available diameter, the bar count is the larger of the one that covers the required area and the one that keeps the bars, evenly spread over the band, within the largest spacing. The layout with the least provided area is kept; on a tie, the one with fewer bars.

        Args:
            effective_depth: Effective depth d of the section (cm).
            bottom_extent: Distance from the bottom face to the inner edge of the last bottom bars (cm).
            top_extent: Distance from the top face to the inner edge of the last top bars (cm).

        Raises:
            ValueError: If the bottom and top bars leave no band between them.

        References:
            ABNT NBR 6118:2026 — Section 17.3.5.2.3
            ABNT NBR 6118:2026 — Section 18.3.5
        """
        band_start = bottom_extent  # cm
        band_end = self.beam.height - top_extent  # cm
        band_height = band_end - band_start  # cm
        if band_height <= 0:
            raise ValueError(
                f"No room for skin reinforcement: the bottom bars ({bottom_extent:.2f} cm) "
                f"and the top bars ({top_extent:.2f} cm) fill the {self.beam.height:g} cm web."
            )
        required_area = self.required_area  # cm²
        options: list[SkinLayout] = []
        for diameter_mm in self.steel.available_sizes:
            bar_area = section.circular_cross_sectional_area(diameter_mm / 10)  # cm²
            spacing_limit = self.max_spacing(effective_depth, diameter_mm)  # cm
            bars = max(
                ceil(required_area / bar_area),
                ceil(band_height / spacing_limit) - 1,
                1,
            )
            options.append(
                SkinLayout(
                    diameter_mm=diameter_mm,
                    bars_per_face=bars,
                    spacing=band_height / (bars + 1),
                    band_start=band_start,
                    band_end=band_end,
                )
            )
        layout = min(
            options, key=lambda option: (option.area_per_face, option.bars_per_face)
        )
        log_operation(
            f"Skin band {band_start:.2f}–{band_end:.2f} cm from the bottom face; "
            f"As,skin = {required_area:.3f} cm²/face; {layout.bars_per_face} φ{layout.diameter_mm:g} c/{layout.spacing:.1f} cm "
            f"({layout.area_per_face:.3f} cm²/face)"
        )
        return layout
