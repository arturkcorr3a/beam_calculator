from dataclasses import dataclass, field
from itertools import count
from typing import Literal, cast

from src.loading.superficial_loads import SuperficialLoads
from src.pavement.pillar import Pillar
from src.pavement.continuous_beam import ContinuousBeam, Span
from src.pavement.slab_edge import Edges, SlabEdge

# TODO review this value and look for references in NBR 6118 (or other source)
SLAB_MIN_THICKNESS = 8.0  # cm

type CornerKey = Literal["bottom_left", "top_left", "bottom_right", "top_right"]

CORNER_EDGE_DICT: dict[Edges, tuple[CornerKey, CornerKey]] = {
    Edges.TOP: ("top_left", "top_right"),
    Edges.BOTTOM: ("bottom_left", "bottom_right"),
    Edges.LEFT: ("top_left", "bottom_left"),
    Edges.RIGHT: ("top_right", "bottom_right"),
}

@dataclass
class Slab:
    """Representation of a rectangular concrete slab bounded by four corner pillars.

    The slab is defined by the IDs of its four corner pillars (ordered arbitrarily). During resolution the slab maps those pillars to concrete corner positions (top/bottom, left/right) and finds the supporting edge beams. Thickness is a preliminary value and its pre-dimensioning calculation is not implemented.
    """
    corner_pillar_ids: tuple[str, str, str, str]

    id: str = field(default="", init=False) 
    supporting_beam_ids: list[str] = field(default_factory=list[str], init=False)
    edges: dict[Edges, SlabEdge] = field(default_factory=dict[Edges, SlabEdge], init=False)
    edge_spans: dict[Edges, list[Span]] = field(default_factory=dict[Edges, list[Span]], init=False)
    corners_pillar_dict: dict[CornerKey, Pillar] = field(default_factory=dict[CornerKey, Pillar], init=False)
    thickness: float = field(default=SLAB_MIN_THICKNESS, init=False)
    permanent_load: float = field(default=0.0, init=False) 
    variable_load: float = field(default=0.0, init=False)

    _counter = count(1)  # Class-level counter for auto-generating IDs

    def __post_init__(self):
        self.id = f"L{next(self._counter)}"  # Auto-generate ID if not provided
        self._validate_pillar_count()
        self._setup_edges()

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

    # IMPLEMENT this is going to be more complex (pre-dimensioning is done through ELS analysis)
    def pre_size(self) -> bool:
        """Sets the slab's thickness and return True if the slab is stable (there weren't any changes in thickness or support conditions that require re-validation of the pavement structure)."""
        return True  # IMPLEMENT Placeholder implementation; always returns True for now

    @property
    def dimensions(self) -> tuple[float, float]:
        """X and y dimensions of the slab (cm)."""
        x_dimension = cast(float, self.edges[Edges.RIGHT].beam.centerline) - cast(float, self.edges[Edges.LEFT].beam.centerline)
        y_dimension = cast(float, self.edges[Edges.TOP].beam.centerline) - cast(float, self.edges[Edges.BOTTOM].beam.centerline)
        return (x_dimension, y_dimension)

    def add_permanent_load(self, load: float) -> None:
        """Adds a permanent load (kN/m²) to the slab's total permanent load."""
        self.permanent_load += load

    def resolve_variable_load(self, local: str) -> None:
        """Sets the variable load (kN/m²) to the slab's total variable load depending on the local."""
        self.variable_load = SuperficialLoads.get_variable_usage_load(local)

    def resolve_and_validate(self, pillar_registry: dict[str, Pillar], beam_registry: dict[str, ContinuousBeam]) -> None:
        """Resolves supporting beams and validates the slab's rectangle."""
        self._validate_pillars_exist(pillar_registry)
        self._map_pillars_to_corners(pillar_registry)
        self._resolve_supporting_beams(beam_registry)
        self._add_slab_to_spans()

    def unload_on_supporting_spans(self, pillar_registry: dict[str, Pillar]) -> None:
        """Unloads the slab's load on its supporting spans."""
        self.resolve_influence_areas()
        for edge in Edges:
            self.edges[edge].unload_on_spans(pillar_registry)

    # PAPER get reference for this (metodo das charneiras -> norma ou literatura)
    # IMPLEMENT calculate the influence areas for each edge
    def resolve_influence_areas(self) -> None:
        # IMPLEMENT placeholder function -> proportional to the side length
        lx_cm, ly_cm = self.dimensions
        lx, ly = lx_cm / 100, ly_cm / 100
        x_ratio = lx / (lx + ly)
        y_ratio = ly / (lx + ly)
        area = lx * ly  # m²

        self.edges[Edges.TOP].influence_area = x_ratio * area
        self.edges[Edges.BOTTOM].influence_area = x_ratio * area
        self.edges[Edges.LEFT].influence_area = y_ratio * area
        self.edges[Edges.RIGHT].influence_area = y_ratio * area

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate_pillars_exist(self, pillar_registry: dict[str, Pillar]) -> None:
        """Ensures all pillar_ids exist in the provided pillar_registry."""
        for pillar_id in self.corner_pillar_ids:
            if pillar_id not in pillar_registry:
                raise ValueError(f"Beam '{self.id}': pillar '{pillar_id}' does not exist in the registry.")

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

    def _resolve_supporting_beams(self, beam_registry: dict[str, ContinuousBeam]) -> None:
        """Resolves the supporting beams (and respective spans) for each edge of the slab."""
        for edge in Edges:
            self._resolve_edge(edge, beam_registry)

    def _resolve_edge(self, edge: Edges, beam_registry: dict[str, ContinuousBeam]) -> ContinuousBeam:
        "Finds the beam (and respective spans) that supports a given edge of the slab."
        corner_1, corner_2 = CORNER_EDGE_DICT[edge]
        corner_pillar_1 = self.corners_pillar_dict[corner_1]
        corner_pillar_2 = self.corners_pillar_dict[corner_2]

        for beam in beam_registry.values():
            if beam.contains_pillar(corner_pillar_1.id) and beam.contains_pillar(corner_pillar_2.id):
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