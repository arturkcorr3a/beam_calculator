import math
from dataclasses import dataclass, field
from functools import cached_property
from itertools import count
from typing import Literal, NamedTuple, assert_never, cast

from src.checkers.deformation_check_result import DeformationCheckResult
from src.checkers.slab_deformation_checker import SlabDeformationChecker
from src.config import APP_CONFIG
from src.config_options import ExposureClass
from src.errors import (
    SlabInputError,
    SlabLoweredTooMuchError,
    SlabThicknessExceededError,
    UnknownPillarError,
)
from src.loading.superficial_loads import SuperficialLoads
from src.logger import (
    log_element,
    log_iteration,
    log_operation,
    log_property,
    logger_label,
)
from src.pavement_elements.continuous_beam import ContinuousBeam
from src.pavement_elements.geometry_utils import (
    Point,
    calculate_polygon_area,
    effective_span,
)
from src.pavement_elements.pillar import Pillar
from src.pavement_elements.slab_edge import Edges, SlabEdge, SupportCondition

SLAB_MIN_THICKNESS = 8  # cm; from ABNT NBR 6118 - Section 12.4.1

ONE_WAY_SLAB_THRESHOLD_RATIO = 2.0  # Based on Based on 'Cálculo e Detalhamento de Estruturas Usuais de Concreto Armado', item 7.3.
DEFAULT_WIDTH = 100  # cm; default width for slabs, used in pre-sizing calculation
MAX_THICKNESS_FLOAT_TOLERANCE = 1e-9  # cm; absorbs float drift in the effective spans

type CornerKey = Literal["bottom_left", "top_left", "bottom_right", "top_right"]

CORNER_EDGE_DICT: dict[Edges, tuple[CornerKey, CornerKey]] = {
    Edges.TOP: ("top_left", "top_right"),
    Edges.BOTTOM: ("bottom_left", "bottom_right"),
    Edges.LEFT: ("top_left", "bottom_left"),
    Edges.RIGHT: ("top_right", "bottom_right"),
}


class PermanentLoadDefinition(NamedTuple):
    """Definition of a permanent load."""

    material_description: str
    weight: float


class _SlabMeta(type):
    @property
    def nominal_covering(self) -> float:
        """
        Returns the nominal covering (cm) for the slab with the configured exposure class, with 10 mm execution tolerance, based on ABNT NBR 6118 - Section 7.4. The table value gets the discount for concrete stronger than the minimum and is then raised, if needed, to the minimum cover allowed by the maximum aggregate size (ABNT NBR 6118 - Section 7.4.7.6).
        """
        exposure_class = APP_CONFIG.exposure_class
        fck = APP_CONFIG.pavement_concrete.value

        discount_for_concrete_greater_than_minimum = (
            0.5 if APP_CONFIG.is_concrete_greater_than_minimum(fck) else 0.0
        )  # cm — ABNT NBR 6118 - Section 7.4.7.6

        match exposure_class:
            case ExposureClass.WEAK:
                table_cover = 2.0
            case ExposureClass.MODERATE:
                table_cover = 2.5
            case ExposureClass.SEVERE:
                table_cover = 3.5
            case ExposureClass.VERY_SEVERE:
                table_cover = 4.5
            case _:
                assert_never(exposure_class)

        return max(
            table_cover - discount_for_concrete_greater_than_minimum,
            APP_CONFIG.minimum_nominal_cover_for_aggregate(),
        )  # cm — ABNT NBR 6118 - Table 7.2 and Section 7.4.7.6


@logger_label("{id}")
@dataclass(eq=False, repr=False)
class Slab(metaclass=_SlabMeta):
    """Representation of a rectangular concrete slab bounded by four corner pillars.

    The slab is defined by the IDs of its four corner pillars (ordered arbitrarily). During resolution the slab maps those pillars to concrete corner positions (top/bottom, left/right) and finds the supporting edge beams.

    Attributes:
        lowered: How far the slab is lowered below the floor level (cm). A
            lowered slab is always pinned on its edges, and its neighbours
            treat it as if there were no slab. It must not exceed max_lowered.
    """

    corner_pillar_ids: tuple[str, str, str, str]
    local: str

    id: str = field(default="", kw_only=True)  # empty: generated from the counter
    supporting_beam_ids: list[str] = field(default_factory=list[str], init=False)
    edges: dict[Edges, SlabEdge] = field(
        default_factory=dict[Edges, SlabEdge], init=False
    )
    corners_pillar_dict: dict[CornerKey, Pillar] = field(
        default_factory=dict[CornerKey, Pillar], init=False
    )
    thickness: int = field(default=SLAB_MIN_THICKNESS, init=False)
    permanent_load: float = field(default=0.0, init=False)
    variable_load: float = field(default=0.0, init=False)

    top_finish: PermanentLoadDefinition = field(
        default=PermanentLoadDefinition("", 0.0)
    )
    ceiling_finish: str = field(default="")
    infill: PermanentLoadDefinition = field(default=PermanentLoadDefinition("", 0.0))
    lowered: int = 0  # cm
    deflection_check: DeformationCheckResult | None = field(
        default=None, init=False
    )  # ELS-DEF verification at the pre-sized thickness
    deflection_support_case: int | None = field(
        default=None, init=False
    )  # Carvalho Quadro 7.2 case (1-9) of that verification

    _counter = count(1)  # Class-level counter for auto-generating IDs

    @classmethod
    def reset_id_counter(cls) -> None:
        """Restart auto-generated ids at 1 (L1)"""
        cls._counter = count(1)

    def __repr__(self) -> str:
        """Identity only: the edges reference the supporting beams, whose full repr
        would pull in their whole dimensioning"""
        return f"Slab(id={self.id!r}, corner_pillar_ids={self.corner_pillar_ids!r})"

    def __post_init__(self):
        if not self.id:
            self.id = f"L{next(self._counter)}"
        self._validate_pillar_count()
        self._validate_lowered_not_negative()
        self._setup_edges()

    @property
    def is_lowered(self) -> bool:
        return self.lowered > 0

    @property
    def max_lowered(self) -> float:
        """Return the maximum lowering (cm) allowed for the slab

        The bottom face of every supporting beam must not sit above the slab's
        bottom face, so the limit is the shortest supporting beam's height
        minus the slab thickness.
        """
        return self._shortest_supporting_beam().height - self.thickness

    def _shortest_supporting_beam(self) -> ContinuousBeam:
        return min(
            (edge.beam for edge in self.edges.values()), key=lambda beam: beam.height
        )

    def _validate_lowered_not_negative(self) -> None:
        if self.lowered < 0:
            raise SlabInputError(
                f"Slab '{self.id}': lowered must be >= 0 cm, got {self.lowered}.",
                slab_id=self.id,
            )

    def validate_lowered(self) -> None:
        """Check that the lowering fits within the shortest supporting beam

        Raises:
            SlabLoweredTooMuchError: If lowered exceeds max_lowered.
        """
        if self.lowered > self.max_lowered:
            beam = self._shortest_supporting_beam()
            raise SlabLoweredTooMuchError(
                slab_id=self.id,
                lowered=self.lowered,
                max_lowered=self.max_lowered,
                beam_id=beam.id,
                beam_height=beam.height,
                thickness=self.thickness,
            )

    def resolve_support_conditions(self, pillar_registry: dict[str, Pillar]) -> None:
        """Resolve the support condition of each of the slab's edges"""
        for edge in self.edges.values():
            edge.resolve_support_condition(pillar_registry)

    def _current_support_conditions(self) -> dict[Edges, SupportCondition]:
        return {edge: self.edges[edge].support_condition for edge in Edges}

    @staticmethod
    def _corner_yield_slope(
        horizontal_cond: SupportCondition,
        vertical_cond: SupportCondition,
        horizontal_and_vertical_labels: tuple[str, str] = ("horizontal", "vertical"),
    ) -> float:
        """Returns the yield-line slope (tan theta) at a corner, where theta is measured from the horizontal edge, based on ABNT NBR 6118 - Section 14.7.6.1.

        - Both same: 45 degrees (1.0).
        - Horizontal fixed, vertical pinned: 60 degrees (sqrt(3)).
        - Horizontal pinned, vertical fixed: 30 degrees (1/sqrt(3)).
        """
        if horizontal_cond == vertical_cond:
            log_property(
                f"{horizontal_and_vertical_labels[0]} = {horizontal_cond}, {horizontal_and_vertical_labels[1]} = {vertical_cond} => 45° (1.0)"
            )
            return 1.0
        if horizontal_cond == "fixed":
            log_property(
                f"{horizontal_and_vertical_labels[0]} = {horizontal_cond}, {horizontal_and_vertical_labels[1]} = {vertical_cond} => 60° (sqrt(3))"
            )
            return math.sqrt(3)
        log_property(
            f"{horizontal_and_vertical_labels[0]} = {horizontal_cond}, {horizontal_and_vertical_labels[1]} = {vertical_cond} => 30° (1/sqrt(3))"
        )
        return 1.0 / math.sqrt(3)

    # PAPER get reference for the one-way strip reaction coefficients
    @staticmethod
    def _one_way_reaction_fraction(
        own: SupportCondition, opposite: SupportCondition
    ) -> float:
        """Return the fraction of a one-way slab's load carried by one supporting edge

        The slab is treated as a strip spanning the short direction between the
        two long edges, under uniform load. Pinned-pinned and fixed-fixed strips
        split the load equally; a fixed-pinned strip sends 5/8 to the fixed end
        and 3/8 to the pinned end.

        Args:
            own: Support condition of the edge whose fraction is returned.
            opposite: Support condition of the opposite (parallel) edge.

        Returns:
            Fraction of the slab's total load carried by the edge, in [0, 1].
        """
        if own == opposite:
            return 0.5
        if own == "fixed":
            return 5.0 / 8.0
        return 3.0 / 8.0

    def _setup_edges(self) -> None:
        """Initializes the edges dictionary with SlabEdge instances for each edge."""
        self.edges = {edge: SlabEdge(edge, self) for edge in Edges}

    def clear_resolved(self) -> None:
        self.supporting_beam_ids = []
        self.corners_pillar_dict = {}
        self.deflection_check = None
        self.deflection_support_case = None
        for edge in self.edges.values():
            edge.clear_resolved()

    def _validate_pillar_count(self) -> None:
        if len(self.corner_pillar_ids) != 4:
            raise SlabInputError(
                f"Slab '{self.id}' must have exactly 4 corner pillars.", slab_id=self.id
            )

    def pre_size(self, pillar_registry: dict[str, Pillar]) -> bool:
        """Set the slab's thickness to the minimum value that passes ELS-DEF verification.

        The edge support conditions are re-resolved at every thickness tried,
        since they depend on the thickness difference to the adjacent slabs.
        The passing verification is kept in ``deflection_check`` and
        ``deflection_support_case``.

        Args:
            pillar_registry: Mapping of pillar ID to Pillar, used to measure
                span lengths when resolving support conditions.

        Returns:
            True if the slab is stable (thickness was unchanged, no re-validation needed).
        """
        original_thickness = self.thickness
        self.thickness = SLAB_MIN_THICKNESS

        self.resolve_support_conditions(pillar_registry)
        support_conditions = self._current_support_conditions()

        lx, ly = self.effective_dimensions
        checker = SlabDeformationChecker(
            permanent_load=self.permanent_load,
            variable_load=self.variable_load,
            usage=self.local,
            lx=lx,
            ly=ly,
            support_conditions=support_conditions,
            id=self.id,
        )
        while not checker.verify(self.thickness):
            log_iteration(f"h = {self.thickness} cm: fail")
            self.thickness += 1
            if self.thickness > self.max_thickness:
                raise SlabThicknessExceededError(
                    slab_id=self.id, max_thickness=self.max_thickness
                )
            # The effective spans depend on the thickness (0.3 h cap)
            checker.lx, checker.ly = self.effective_dimensions
            checker.span = min(checker.lx, checker.ly)
            self.resolve_support_conditions(pillar_registry)
            checker.support_conditions = self._current_support_conditions()

        self.deflection_check = checker.result()
        self.deflection_support_case = checker.supporting_case

        thickness_changed = self.thickness != original_thickness
        if thickness_changed:
            log_iteration(f"h = {self.thickness} cm: pass")
        else:
            log_iteration(f"h = {self.thickness} cm: no change")
        log_element(f"Thickness = {self.thickness} cm")
        return not thickness_changed

    @cached_property
    def dimensions(self) -> tuple[float, float]:
        """x and y distances (cm) between the supporting beams' centerlines, in that order."""
        x_dimension = cast(float, self.edges[Edges.RIGHT].beam.centerline) - cast(
            float, self.edges[Edges.LEFT].beam.centerline
        )
        y_dimension = cast(float, self.edges[Edges.TOP].beam.centerline) - cast(
            float, self.edges[Edges.BOTTOM].beam.centerline
        )
        return (x_dimension, y_dimension)

    @property
    def effective_dimensions(self) -> tuple[float, float]:
        """Return the slab's effective spans along x and y (cm), in that order

        Each span is reduced from the centroid distance between the supporting
        beams using the beam widths and the slab thickness (0.3 h cap). Not
        cached, since the thickness changes during pre-sizing.

        References:
            ABNT NBR 6118:2014 — Section 14.7.2.2
        """
        # NOTE the 0.3 * h cap is disabled for now; see effective_span() for details
        x_dimension, y_dimension = self.dimensions
        effective_x = effective_span(
            x_dimension,
            self.edges[Edges.LEFT].beam.width,
            self.edges[Edges.RIGHT].beam.width,
            self.thickness,
        )
        effective_y = effective_span(
            y_dimension,
            self.edges[Edges.BOTTOM].beam.width,
            self.edges[Edges.TOP].beam.width,
            self.thickness,
        )
        return (effective_x, effective_y)

    @property
    def is_one_way(self) -> bool:
        """Returns True if the slab is a one-way slab, based on the ratio of its effective spans.

        Based on 'Cálculo e Detalhamento de Estruturas Usuais de Concreto Armado', item 7.3."""
        biggest = max(self.effective_dimensions)
        smallest = min(self.effective_dimensions)
        return (biggest / smallest) > ONE_WAY_SLAB_THRESHOLD_RATIO

    def add_permanent_load(self, load: float) -> None:
        """Adds a permanent load (kN/m²) to the slab's total permanent load."""
        self.permanent_load += load

    @property
    def total_permanent_load(self) -> float:
        """Permanent load (kN/m²) including the slab's own weight at the current thickness

        ``permanent_load`` holds the finishes only; the own weight is added here
        so it reaches the supporting beams once the thickness is final.

        References:
            ABNT NBR 6120:2019 — Table 1
        """
        return self.permanent_load + SuperficialLoads.get_concrete_element_own_weight(
            self.thickness / 100
        )

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
        self._resolve_permanent_load_without_own_weight()
        self._resolve_variable_load()
        lx, ly = self.effective_dimensions
        log_element(
            f"{'One-way' if self.is_one_way else 'Two-way'}; {lx / 100.0:.2f} x {ly / 100.0:.2f} m; Variable load: {self.variable_load:.1f} kN/m2"
        )

    def unload_on_supporting_spans(self, pillar_registry: dict[str, Pillar]) -> None:
        """Unloads the slab's load on its supporting spans."""
        self.resolve_influence_areas()
        for edge in Edges:
            if self.edges[edge].influence_area <= 0.0:
                continue
            self.edges[edge].unload_on_spans(pillar_registry)

    def resolve_influence_areas(self) -> None:
        """Calculates each edge's influence area (m²).

        Two-way slabs use the Yield Line Theory, based on ABNT NBR 6118 - Section 14.7.6.1.
        One-way slabs load only the two long edges (see _resolve_one_way_influence_areas).
        """
        lx_cm, ly_cm = self.effective_dimensions
        lx, ly = lx_cm / 100, ly_cm / 100

        if self.is_one_way:
            self._resolve_one_way_influence_areas(lx, ly)
        else:
            self._resolve_two_way_influence_areas(lx, ly)

        for edge in Edges:
            log_operation(
                f"{edge.value} influence area = {self.edges[edge].influence_area:.4f} m²"
            )

    def _resolve_one_way_influence_areas(self, lx: float, ly: float) -> None:
        """Distribute a one-way slab's area between its two long edges

        The slab spans the short direction, so only the beams along the long
        edges support it; the short edges receive no load.

        Args:
            lx: Slab dimension along x (m).
            ly: Slab dimension along y (m).

        References:
            Carvalho & Figueiredo Filho — Cálculo e Detalhamento de Estruturas
                Usuais de Concreto Armado, item 7.3.
        """
        if lx > ly:
            supporting, unsupported = (
                (Edges.BOTTOM, Edges.TOP),
                (Edges.LEFT, Edges.RIGHT),
            )
        else:
            supporting, unsupported = (
                (Edges.LEFT, Edges.RIGHT),
                (Edges.BOTTOM, Edges.TOP),
            )

        total_area = lx * ly
        edge_a, edge_b = supporting

        condition_a = self.edges[edge_a].support_condition
        condition_b = self.edges[edge_b].support_condition

        fraction_a = Slab._one_way_reaction_fraction(condition_a, condition_b)
        fraction_b = Slab._one_way_reaction_fraction(condition_b, condition_a)

        log_operation(
            f"One-way: {edge_a.value} ({condition_a}) = {fraction_a:.3f}, {edge_b.value} ({condition_b}) = {fraction_b:.3f}"
        )

        self.edges[edge_a].influence_area = total_area * fraction_a
        self.edges[edge_b].influence_area = total_area * fraction_b
        # each region starts with its edge's two corners, counter-clockwise
        if edge_a is Edges.BOTTOM:
            split = fraction_a * ly
            self.edges[edge_a].influence_polygon = (
                Point(0, 0),
                Point(lx, 0),
                Point(lx, split),
                Point(0, split),
            )
            self.edges[edge_b].influence_polygon = (
                Point(lx, ly),
                Point(0, ly),
                Point(0, split),
                Point(lx, split),
            )
        else:
            split = fraction_a * lx
            self.edges[edge_a].influence_polygon = (
                Point(0, ly),
                Point(0, 0),
                Point(split, 0),
                Point(split, ly),
            )
            self.edges[edge_b].influence_polygon = (
                Point(lx, 0),
                Point(lx, ly),
                Point(split, ly),
                Point(split, 0),
            )

        for edge in unsupported:
            self.edges[edge].influence_area = 0.0
            self.edges[edge].influence_polygon = ()

    def _resolve_two_way_influence_areas(self, lx: float, ly: float) -> None:
        """Calculates each edge's influence area (m²) using the Yield Line Theory, based on ABNT NBR 6118 - Section 14.7.6.1."""

        slope_bl = Slab._corner_yield_slope(
            self.edges[Edges.BOTTOM].support_condition,
            self.edges[Edges.LEFT].support_condition,
            ("bottom", "left"),
        )
        slope_br = Slab._corner_yield_slope(
            self.edges[Edges.BOTTOM].support_condition,
            self.edges[Edges.RIGHT].support_condition,
            ("bottom", "right"),
        )
        slope_tl = Slab._corner_yield_slope(
            self.edges[Edges.TOP].support_condition,
            self.edges[Edges.LEFT].support_condition,
            ("top", "left"),
        )
        slope_tr = Slab._corner_yield_slope(
            self.edges[Edges.TOP].support_condition,
            self.edges[Edges.RIGHT].support_condition,
            ("top", "right"),
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

        # each region starts with its edge's two corners, counter-clockwise
        if p_bottom.y < p_left.y:
            # Vertical pattern: BOTTOM/TOP → triangles; LEFT/RIGHT → quadrilaterals
            polygons = {
                Edges.BOTTOM: (p_bl, p_br, p_bottom),
                Edges.TOP: (p_tr, p_tl, p_top),
                Edges.LEFT: (p_tl, p_bl, p_bottom, p_top),
                Edges.RIGHT: (p_br, p_tr, p_top, p_bottom),
            }
        else:
            # Horizontal pattern: LEFT/RIGHT → triangles; BOTTOM/TOP → quadrilaterals
            polygons = {
                Edges.LEFT: (p_tl, p_bl, p_left),
                Edges.RIGHT: (p_br, p_tr, p_right),
                Edges.BOTTOM: (p_bl, p_br, p_right, p_left),
                Edges.TOP: (p_tr, p_tl, p_left, p_right),
            }
        for edge, polygon in polygons.items():
            self.edges[edge].influence_polygon = polygon
            self.edges[edge].influence_area = calculate_polygon_area(list(polygon))

    @property
    def max_thickness(self) -> int:
        """
        Return the largest whole thickness (cm) for the slab to remain a surface.

        References:
            ABNT NBR 6118:2026 — Section 14.4.2.1
        """
        limit = min(self.effective_dimensions) / 3  # cm
        return math.floor(limit + MAX_THICKNESS_FLOAT_TOLERANCE)  # cm

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate_pillars_exist(self, pillar_registry: dict[str, Pillar]) -> None:
        """Ensures all pillar_ids exist in the provided pillar_registry."""
        for pillar_id in self.corner_pillar_ids:
            if pillar_id not in pillar_registry:
                raise UnknownPillarError(
                    owner_kind="Slab", owner_id=self.id, pillar_id=pillar_id
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
        """Find the beam (and respective spans) that supports a given edge of the slab

        Raises:
            SlabInputError: If no beam contains both corner pillars of the edge,
                or if the beam has no span between them (e.g. both corners are
                the same pillar).
        """
        corner_1, corner_2 = CORNER_EDGE_DICT[edge]
        corner_pillar_1 = self.corners_pillar_dict[corner_1]
        corner_pillar_2 = self.corners_pillar_dict[corner_2]

        for beam in beam_registry.values():
            if beam.contains_pillar(corner_pillar_1.id) and beam.contains_pillar(
                corner_pillar_2.id
            ):
                spans = beam.get_spans_between(corner_pillar_1.id, corner_pillar_2.id)
                if not spans:
                    raise SlabInputError(
                        f"Slab '{self.id}': {edge.value} edge has no span between pillars '{corner_pillar_1.id}' and '{corner_pillar_2.id}' on beam '{beam.id}'.",
                        slab_id=self.id,
                    )
                self.edges[edge].resolve_beam(beam)
                self.edges[edge].resolve_spans(spans)
                return beam
        raise SlabInputError(
            f"Slab '{self.id}': No valid beam found for {edge.value} edge.",
            slab_id=self.id,
        )

    def _add_slab_to_spans(self) -> None:
        """Adds the slab to the span's supported_slabs."""
        for edge in Edges:
            for span in self.edges[edge].spans:
                span.add_supported_slab(self)

    def _resolve_permanent_load_without_own_weight(self) -> None:
        """Sets the permanent load (kN/m²) to the slab's total permanent load depending on the local."""
        log_operation("Resolving permanent load (no own weight)...")
        self.permanent_load = (
            SuperficialLoads.get_top_finish_weight(*(self.top_finish))
            + SuperficialLoads.get_ceiling_weight(self.ceiling_finish)
            + SuperficialLoads.get_infill_weight(*(self.infill))
        )

    def _resolve_variable_load(self) -> None:
        """Sets the variable load (kN/m²) to the slab's total variable load depending on the local."""
        log_operation("Resolving variable load...")
        self.variable_load = SuperficialLoads.get_variable_usage_load(self.local)
