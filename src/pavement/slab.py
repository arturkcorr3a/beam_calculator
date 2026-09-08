import math
from dataclasses import dataclass, field
from functools import cached_property
from itertools import count
from typing import Literal, cast

from src.config import APP_CONFIG
from src.loading.slab_deformation_checker import SlabDeformationChecker
from src.loading.superficial_loads import SuperficialLoads
from src.logger import (
    log_element,
    log_iteration,
    log_operation,
    log_property,
    logger_label,
)
from src.pavement.continuous_beam import ContinuousBeam, Span
from src.pavement.geometry_utils import Point, calculate_polygon_area
from src.pavement.pillar import Pillar
from src.pavement.slab_edge import Edges, SlabEdge, SupportCondition
from src.properties.concrete import Concrete

SLAB_MIN_THICKNESS = 8  # cm; from ABNT NBR 6118 - Section 12.4.1

ONE_WAY_SLAB_THRESHOLD_RATIO = 2.0  # Based on Based on 'Cálculo e Detalhamento de Estruturas Usuais de Concreto Armado', item 7.3.
DEFAULT_WIDTH = 100  # cm; default width for slabs, used in pre-sizing calculation

type CornerKey = Literal["bottom_left", "top_left", "bottom_right", "top_right"]

CORNER_EDGE_DICT: dict[Edges, tuple[CornerKey, CornerKey]] = {
    Edges.TOP: ("top_left", "top_right"),
    Edges.BOTTOM: ("bottom_left", "bottom_right"),
    Edges.LEFT: ("top_left", "bottom_left"),
    Edges.RIGHT: ("top_right", "bottom_right"),
}


class _BeamMeta(type):
    @property
    def nominal_covering(self) -> float:
        """
        Returns the nominal covering (cm) for the slab with the configured exposure class, with 10 mm execution tolerance, based on ABNT NBR 6118 - Section 7.4.
        """
        exposure_class = APP_CONFIG.exposure_class
        match exposure_class:
            case 1:
                return 2.0
            case 2:
                return 2.5
            case 3:
                return 3.5
            case 4:
                return 4.5
            case _:
                raise ValueError(
                    f"Invalid exposure class: {exposure_class}. Must be between 1 and 4."
                )


@logger_label("{id}")
@dataclass
class Slab(metaclass=_BeamMeta):
    """Representation of a rectangular concrete slab bounded by four corner pillars.

    The slab is defined by the IDs of its four corner pillars (ordered arbitrarily). During resolution the slab maps those pillars to concrete corner positions (top/bottom, left/right) and finds the supporting edge beams.
    """

    corner_pillar_ids: tuple[str, str, str, str]
    local: str

    id: str = field(default="", init=False)
    supporting_beam_ids: list[str] = field(default_factory=list[str], init=False)
    edges: dict[Edges, SlabEdge] = field(
        default_factory=dict[Edges, SlabEdge], init=False
    )
    edge_spans: dict[Edges, list[Span]] = field(
        default_factory=dict[Edges, list[Span]], init=False
    )
    corners_pillar_dict: dict[CornerKey, Pillar] = field(
        default_factory=dict[CornerKey, Pillar], init=False
    )
    thickness: int = field(default=SLAB_MIN_THICKNESS, init=False)
    permanent_load: float = field(default=0.0, init=False)
    variable_load: float = field(default=0.0, init=False)

    _counter = count(1)  # Class-level counter for auto-generating IDs

    def __post_init__(self):
        self.id = f"L{next(self._counter)}"  # Auto-generate ID if not provided
        self._validate_pillar_count()
        self._setup_edges()

    @staticmethod
    def _corner_yield_slope(
        horizontal_cond: SupportCondition, vertical_cond: SupportCondition
    ) -> float:
        """Returns the yield-line slope (tan theta) at a corner, where theta is measured from the horizontal edge, based on ABNT NBR 6118 - Section 14.7.6.1.

        - Both same: 45 degrees (1.0).
        - Horizontal fixed, vertical pinned: 60 degrees (sqrt(3)).
        - Horizontal pinned, vertical fixed: 30 degrees (1/sqrt(3)).
        """
        if horizontal_cond == vertical_cond:
            return 1.0
        if horizontal_cond == "fixed":
            return math.sqrt(3)
        return 1.0 / math.sqrt(3)

    def _setup_edges(self) -> None:
        """Initializes the edges dictionary with SlabEdge instances for each edge."""
        self.edges = {edge: SlabEdge(edge, self) for edge in Edges}

    def clear_resolved(self) -> None:
        self.supporting_beam_ids = []
        self.corners_pillar_dict = {}
        for edge in self.edges.values():
            edge.clear_resolved()

    def _validate_pillar_count(self) -> None:
        if len(self.corner_pillar_ids) != 4:
            raise ValueError(f"Slab '{self.id}' must have exactly 4 corner pillars.")

    def pre_size(self) -> bool:
        """Set the slab's thickness to the minimum value that passes ELS-DEF verification.

        Returns:
            True if the slab is stable (thickness was unchanged, no re-validation needed).
        """
        original_thickness = self.thickness
        self.thickness = SLAB_MIN_THICKNESS
        concrete = Concrete[APP_CONFIG.pavement_concrete]

        support_conditions: dict[Edges, SupportCondition] = {
            edge: self.edges[edge].support_condition for edge in Edges
        }

        lx, ly = self.dimensions
        checker = SlabDeformationChecker(
            permanent_load=self.permanent_load,
            variable_load=self.variable_load,
            usage=self.local,
            concrete=concrete,
            lx=lx,
            ly=ly,
            support_conditions=support_conditions,
        )
        while not checker.verify(self.thickness):
            log_iteration(f"h = {self.thickness} cm: fail")
            self.thickness += 1
            if self.thickness > self.max_thickness:
                raise ValueError(
                    f"Slab '{self.id}' cannot be stabilized; required thickness exceeds 30 cm."
                )

        log_element(f"thickness = {self.thickness} cm")
        thickness_changed = self.thickness != original_thickness
        return not thickness_changed

    @cached_property
    def dimensions(self) -> tuple[float, float]:
        """X and y dimensions of the slab (cm)."""
        x_dimension = cast(float, self.edges[Edges.RIGHT].beam.centerline) - cast(
            float, self.edges[Edges.LEFT].beam.centerline
        )
        y_dimension = cast(float, self.edges[Edges.TOP].beam.centerline) - cast(
            float, self.edges[Edges.BOTTOM].beam.centerline
        )
        return (x_dimension, y_dimension)

    @cached_property
    def is_one_way(self) -> bool:
        """Returns True if the slab is a one-way slab, based on the ratio of its dimensions.

        Based on 'Cálculo e Detalhamento de Estruturas Usuais de Concreto Armado', item 7.3."""
        biggest = max(self.dimensions)
        smallest = min(self.dimensions)
        return (biggest / smallest) <= ONE_WAY_SLAB_THRESHOLD_RATIO

    def add_permanent_load(self, load: float) -> None:
        """Adds a permanent load (kN/m²) to the slab's total permanent load."""
        self.permanent_load += load

    def resolve_and_validate(
        self,
        pillar_registry: dict[str, Pillar],
        beam_registry: dict[str, ContinuousBeam],
    ) -> None:
        """Resolves supporting beams and validates the slab's rectangle."""
        self._validate_pillars_exist(pillar_registry)
        self._map_pillars_to_corners(pillar_registry)
        self._resolve_supporting_beams(beam_registry)
        self._add_slab_to_spans()
        self._resolve_variable_load()
        lx, ly = self.dimensions
        log_operation(
            f"{'one-way' if self.is_one_way else 'two-way'}, {lx:.0f} x {ly:.0f} cm, variable load {self.variable_load:.1f} kN/m2"
        )

    def unload_on_supporting_spans(self, pillar_registry: dict[str, Pillar]) -> None:
        """Unloads the slab's load on its supporting spans."""
        self.resolve_influence_areas()
        for edge in Edges:
            self.edges[edge].unload_on_spans(pillar_registry)

    def resolve_influence_areas(self) -> None:
        """Calculates each edge's influence area (m²) using the Yield Line Theory, based on based on ABNT NBR 6118 - Section 14.7.6.1."""
        lx_cm, ly_cm = self.dimensions
        lx, ly = lx_cm / 100, ly_cm / 100

        slope_bl = Slab._corner_yield_slope(
            self.edges[Edges.BOTTOM].support_condition,
            self.edges[Edges.LEFT].support_condition,
        )
        slope_br = Slab._corner_yield_slope(
            self.edges[Edges.BOTTOM].support_condition,
            self.edges[Edges.RIGHT].support_condition,
        )
        slope_tl = Slab._corner_yield_slope(
            self.edges[Edges.TOP].support_condition,
            self.edges[Edges.LEFT].support_condition,
        )
        slope_tr = Slab._corner_yield_slope(
            self.edges[Edges.TOP].support_condition,
            self.edges[Edges.RIGHT].support_condition,
        )

        p_bl = Point(0, 0)
        p_br = Point(lx, 0)
        p_tl = Point(0, ly)
        p_tr = Point(lx, ly)

        p_bottom = Point(
            slope_br * lx / (slope_bl + slope_br),
            slope_bl * slope_br * lx / (slope_bl + slope_br),
        )
        p_top = Point(
            slope_tr * lx / (slope_tl + slope_tr),
            ly - slope_tl * slope_tr * lx / (slope_tl + slope_tr),
        )
        p_left = Point(
            ly / (slope_bl + slope_tl), slope_bl * ly / (slope_bl + slope_tl)
        )
        p_right = Point(
            lx - ly / (slope_br + slope_tr), slope_br * ly / (slope_br + slope_tr)
        )

        if p_bottom.y < p_left.y:
            # Vertical pattern: BOTTOM/TOP → triangles; LEFT/RIGHT → quadrilaterals
            self.edges[Edges.BOTTOM].influence_area = calculate_polygon_area(
                [p_bl, p_br, p_bottom]
            )
            self.edges[Edges.TOP].influence_area = calculate_polygon_area(
                [p_tl, p_tr, p_top]
            )
            self.edges[Edges.LEFT].influence_area = calculate_polygon_area(
                [p_bl, p_bottom, p_top, p_tl]
            )
            self.edges[Edges.RIGHT].influence_area = calculate_polygon_area(
                [p_br, p_tr, p_top, p_bottom]
            )
        else:
            # Horizontal pattern: LEFT/RIGHT → triangles; BOTTOM/TOP → quadrilaterals
            self.edges[Edges.LEFT].influence_area = calculate_polygon_area(
                [p_bl, p_tl, p_left]
            )
            self.edges[Edges.RIGHT].influence_area = calculate_polygon_area(
                [p_br, p_tr, p_right]
            )
            self.edges[Edges.BOTTOM].influence_area = calculate_polygon_area(
                [p_bl, p_br, p_right, p_left]
            )
            self.edges[Edges.TOP].influence_area = calculate_polygon_area(
                [p_tl, p_tr, p_right, p_left]
            )

        for edge in Edges:
            log_property(
                f"{edge.value}: area = {self.edges[edge].influence_area:.4f} m2"
            )

    @property
    def max_thickness(self) -> float:
        """
        It is the max thickness to be considered a surface, Based on ABNT NBR 6118 - Section 14.4.2.1
        """
        return min(self.dimensions) / 3  # cm

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate_pillars_exist(self, pillar_registry: dict[str, Pillar]) -> None:
        """Ensures all pillar_ids exist in the provided pillar_registry."""
        for pillar_id in self.corner_pillar_ids:
            if pillar_id not in pillar_registry:
                raise ValueError(
                    f"Beam '{self.id}': pillar '{pillar_id}' does not exist in the registry."
                )

    def _map_pillars_to_corners(self, pillar_registry: dict[str, Pillar]) -> None:
        """Maps each of the 4 corner pillar IDs to its position: top/bottom-left/right."""
        pillars = [pillar_registry[pillar_id] for pillar_id in self.corner_pillar_ids]
        pillars = sorted(pillars, key=lambda pillar: pillar.y, reverse=True)
        top, bottom = pillars[0:2], pillars[2:4]
        top_left, top_right = sorted(top, key=lambda pillar: pillar.x)
        bottom_left, bottom_right = sorted(bottom, key=lambda pillar: pillar.x)
        self.corners_pillar_dict = {
            "bottom_left": bottom_left,
            "top_left": top_left,
            "bottom_right": bottom_right,
            "top_right": top_right,
        }

    def _resolve_supporting_beams(
        self, beam_registry: dict[str, ContinuousBeam]
    ) -> None:
        """Resolves the supporting beams (and respective spans) for each edge of the slab."""
        for edge in Edges:
            self._resolve_edge(edge, beam_registry)

    def _resolve_edge(
        self, edge: Edges, beam_registry: dict[str, ContinuousBeam]
    ) -> ContinuousBeam:
        "Finds the beam (and respective spans) that supports a given edge of the slab."
        corner_1, corner_2 = CORNER_EDGE_DICT[edge]
        corner_pillar_1 = self.corners_pillar_dict[corner_1]
        corner_pillar_2 = self.corners_pillar_dict[corner_2]

        for beam in beam_registry.values():
            if beam.contains_pillar(corner_pillar_1.id) and beam.contains_pillar(
                corner_pillar_2.id
            ):
                self.edges[edge].resolve_beam(beam)
                spans = beam.get_spans_between(corner_pillar_1.id, corner_pillar_2.id)
                self.edges[edge].resolve_spans(spans)
                return beam
        raise ValueError(f"Slab '{self.id}': No valid beam found for {edge} edge.")

    def _add_slab_to_spans(self) -> None:
        """Adds the slab to the span's supported_slabs."""
        for edge in Edges:
            for span in self.edges[edge].spans:
                span.add_supported_slab(self)

    def _resolve_variable_load(self) -> None:
        """Sets the variable load (kN/m²) to the slab's total variable load depending on the local."""
        self.variable_load = SuperficialLoads.get_variable_usage_load(self.local)
